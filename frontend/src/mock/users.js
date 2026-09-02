/**
 * Mock user registry and dataset registry for the Admin console.
 */
export const USERS = [
  { id: 'USR-001', name: 'Aashish Shrestha', email: 'aashish@example.com', role: 'ADMIN', status: 'ACTIVE', joined: '2024-11-02', lastSeen: '2026-06-09' },
  { id: 'USR-014', name: 'Sita Karki', email: 'sita.k@example.com', role: 'USER', status: 'ACTIVE', joined: '2025-01-18', lastSeen: '2026-06-08' },
  { id: 'USR-027', name: 'Bibek Thapa', email: 'bibek.t@example.com', role: 'USER', status: 'ACTIVE', joined: '2025-03-04', lastSeen: '2026-06-09' },
  { id: 'USR-039', name: 'Puja Gurung', email: 'puja.g@example.com', role: 'USER', status: 'SUSPENDED', joined: '2025-05-21', lastSeen: '2026-05-30' },
  { id: 'USR-048', name: 'Ramesh Adhikari', email: 'ramesh.a@example.com', role: 'USER', status: 'ACTIVE', joined: '2025-08-09', lastSeen: '2026-06-07' },
  { id: 'USR-052', name: 'Nisha Maharjan', email: 'nisha.m@example.com', role: 'USER', status: 'PENDING', joined: '2026-06-01', lastSeen: '2026-06-02' },
]

export const DATASETS = [
  { id: 'DS-NABIL', symbol: 'NABIL', rows: 1375, from: '2021-01-04', to: '2026-06-09', source: 'CSV', updated: '2026-06-09', status: 'READY' },
  { id: 'DS-NICA', symbol: 'NICA', rows: 1375, from: '2021-01-04', to: '2026-06-09', source: 'CSV', updated: '2026-06-09', status: 'READY' },
  { id: 'DS-NTC', symbol: 'NTC', rows: 1375, from: '2021-01-04', to: '2026-06-09', source: 'API', updated: '2026-06-08', status: 'READY' },
  { id: 'DS-UPPER', symbol: 'UPPER', rows: 1340, from: '2021-02-15', to: '2026-06-09', source: 'CSV', updated: '2026-06-05', status: 'PROCESSING' },
  { id: 'DS-CHCL', symbol: 'CHCL', rows: 1120, from: '2021-06-01', to: '2026-06-09', source: 'CSV', updated: '2026-05-28', status: 'STALE' },
]

export const SYSTEM_STATS = {
  totalUsers: 248,
  activeToday: 63,
  ordersToday: 412,
  datasetsTracked: 6,
  modelAccuracy: 0.781,
  lastTrained: '2026-06-07',
}
