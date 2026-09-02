import { useEffect, useRef, useState } from 'react'
import { subscribeMarketStream } from '../lib/ws'

/**
 * Subscribe to the shared market WebSocket and expose the latest tick per symbol
 * plus the connection status. 
 */
export function useMarketStream() {
  const [ticks, setTicks] = useState({})
  const [status, setStatus] = useState('connecting')
  // Hold ticks in a ref so rapid batches coalesce into a single state object.
  const ticksRef = useRef({})

  useEffect(() => {
    const unsubscribe = subscribeMarketStream((msg) => {
      if (msg.type === 'status') {
        setStatus(msg.status)
        return
      }
      if (msg.type === 'tick') {
        const next = { ...ticksRef.current }
        for (const t of msg.data) {
          next[t.symbol] = {
            price: t.price,
            change: t.change,
            change_pct: t.change_pct,
            ts: msg.ts,
          }
        }
        ticksRef.current = next
        setTicks(next)
      }
    })
    return unsubscribe
  }, [])

  return { ticks, status }
}
