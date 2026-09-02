/**
 * Shared market-stream WebSocket client.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

/** Derive ws(s)://host/ws/market from the REST base URL (strip trailing /api). */
export function marketStreamUrl() {
  try {
    const u = new URL(API_BASE, window.location.origin)
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'
    u.pathname = u.pathname.replace(/\/api\/?$/, '') + '/ws/market'
    u.search = ''
    return u.toString()
  } catch {
    return 'ws://localhost:8000/ws/market'
  }
}

const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 15000

let socket = null
let status = 'offline' // 'connecting' | 'live' | 'offline'
let attempts = 0
let reconnectTimer = null
const subscribers = new Set() // fn({ type: 'tick'|'status', data?, status? })

function broadcast(message) {
  for (const fn of subscribers) {
    try {
      fn(message)
    } catch {
      /* a misbehaving subscriber must not break the stream */
    }
  }
}

function setStatus(next) {
  if (status === next) return
  status = next
  broadcast({ type: 'status', status })
}

function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return
  }
  setStatus('connecting')
  let ws
  try {
    ws = new WebSocket(marketStreamUrl())
  } catch {
    scheduleReconnect()
    return
  }
  socket = ws

  ws.onopen = () => {
    attempts = 0
    setStatus('live')
  }
  ws.onmessage = (event) => {
    let msg
    try {
      msg = JSON.parse(event.data)
    } catch {
      return
    }
    if (msg?.type === 'tick' && Array.isArray(msg.data)) {
      broadcast({ type: 'tick', data: msg.data, ts: msg.ts })
    }
  }
  ws.onclose = () => {
    socket = null
    setStatus('offline')
    scheduleReconnect()
  }
  ws.onerror = () => {
    // onclose fires after onerror and drives the reconnect.
    try {
      ws.close()
    } catch {
      /* ignore */
    }
  }
}

function scheduleReconnect() {
  if (reconnectTimer || subscribers.size === 0) return
  const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempts, RECONNECT_MAX_MS)
  attempts += 1
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    if (subscribers.size > 0) connect()
  }, delay)
}

/**
 * Subscribe to the shared stream. The first subscriber opens the connection;
 * the last one to unsubscribe tears it down. Returns an unsubscribe function.
 */
export function subscribeMarketStream(fn) {
  subscribers.add(fn)
  // Hand the new subscriber the current status immediately.
  fn({ type: 'status', status })
  if (subscribers.size === 1) connect()

  return () => {
    subscribers.delete(fn)
    if (subscribers.size === 0) {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (socket) {
        const s = socket
        socket = null
        try {
          s.onclose = null // avoid triggering a reconnect on intentional close
          s.close()
        } catch {
          /* ignore */
        }
      }
      attempts = 0
      status = 'offline'
    }
  }
}
