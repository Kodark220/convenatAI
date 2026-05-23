# convenatAI Dashboard

Agent-to-agent trade execution frontend — built for the hackathon on Arc & GenLayer.

## Stack

- **Next.js 14** (App Router)
- **Framer Motion** — staggered entrances, AnimatePresence, layout animations
- **Recharts** — Jobs/day (bar), USDC/day (area), Agents (line)
- **SWR** — polling every 15s (configurable per route)
- **Tailwind CSS** — utility classes + custom CSS variables
- **DM Mono + Syne** — typography system

---

## Quick Start

```bash
git clone <your-repo>
cd convenat-dashboard
npm install

# Set up env (copy template)
cp .env.example .env.local
# Edit .env.local — leave NEXT_PUBLIC_API_URL empty to run with mock data

npm run dev
# → http://localhost:3000
```

---

## Routes

| Route | Page |
|-------|------|
| `/` | Dashboard — stats, chain status, recent jobs, event feed |
| `/discovery` | Scan Arc/GenLayer, filter results, pick jobs |
| `/agents` | Agent grid with search/filter/pagination |
| `/chains/arc` | Arc Testnet deep-dive: events + 3 charts |
| `/chains/genlayer` | GenLayer ConvenatContract SLA monitor + register_job() form |

---

## Connecting the Backend

All API integration is in **`lib/rpc.ts`**. There are two modes:

### Mock mode (default)
When `NEXT_PUBLIC_API_URL` is empty, the app returns realistic mock data from `lib/rpc.ts`. 
Great for frontend development without a running backend.

### Live mode
Set `NEXT_PUBLIC_API_URL=http://your-backend:port` in `.env.local`.

The app calls these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/stats` | GET | Dashboard stat cards |
| `GET /api/jobs` | GET | Recent jobs list |
| `GET /api/agents` | GET | Agent registry |
| `GET /api/chains/arc/events` | GET | Arc on-chain events |
| `GET /api/chains/genlayer/events` | GET | GenLayer events |
| `GET /api/chains/arc` | GET | Arc chain info |
| `GET /api/chains/genlayer` | GET | GenLayer chain info |
| `GET /api/chains/arc/chart` | GET | 14-day chart data |
| `GET /api/chains/genlayer/chart` | GET | 14-day chart data |
| `GET /api/chains/:chain/scan?from=&to=` | GET | Scan block range |
| `POST /api/genlayer/register-job` | POST | Call register_job() |

### Expected response shapes

See `lib/types.ts` — every type maps 1:1 to an API response.

### Contract addresses

Update in `.env.local`:
```
NEXT_PUBLIC_ARC_CONTRACT=0xYourArcContract
NEXT_PUBLIC_GENLAYER_CONTRACT=0xYourGenLayerContract
```

And update the ABIs in `lib/abi.ts` with the actual deployed ABIs.

---

## File Structure

```
app/
  layout.tsx          → Sidebar + SWR providers
  page.tsx            → Dashboard
  discovery/page.tsx  → Job discovery + scan
  agents/page.tsx     → Agent grid
  chains/arc/page.tsx → Arc deep-dive
  chains/genlayer/page.tsx → GenLayer SLA monitor

components/
  sidebar.tsx         → Sticky nav sidebar
  top-bar.tsx         → Page header + chain indicators + refresh
  stat-card.tsx       → Animated metric cards
  chain-card.tsx      → Chain status cards
  job-table.tsx       → Tabbed jobs table
  event-feed.tsx      → Auto-scrolling live feed
  agent-card.tsx      → Agent grid cards
  scan-form.tsx       → Block range scan UI
  charts.tsx          → Bar, Area, Line recharts
  providers.tsx       → SWR global config

lib/
  types.ts            → All TypeScript types
  rpc.ts              → API fetcher + mock data + endpoint map
  abi.ts              → Contract ABIs + addresses
  utils.ts            → Formatters, color config
```

---

## Polling Intervals

Configurable in `components/providers.tsx` (global) or per-page useSWR call:

- Dashboard: 15s
- Arc events: 10s  
- GenLayer events: 15s
- Stats: 15s

---

## Design Tokens

All colors live in `app/globals.css` as CSS variables. Key ones:

```css
--bg: #08090a
--accent: #5e6ad2
--accent-bright: #7170ff
--success: #10b981
--font-display: 'Syne'
--font-mono: 'DM Mono'
```
