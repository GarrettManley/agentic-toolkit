# HW Dashboard — Web Frontend

Industrial telemetry dashboard for PC hardware upgrade planning.

## Running alongside the API

**Terminal 1 — API server** (from the `apps/hw-dashboard` directory):

```sh
uvicorn api.server:app --host 127.0.0.1 --port 8077
```

**Terminal 2 — Dev server** (from this `web/` directory):

```sh
npm install
npm run dev
```

Open http://localhost:5173. All `/api/*` requests are proxied to `http://127.0.0.1:8077` via the Vite dev-server proxy in `vite.config.ts`.

## Production build

```sh
npm run build   # outputs to dist/
npm run preview # serve dist/ locally
```

## Design

- **Aesthetic**: Industrial telemetry / instrument panel
- **Display font**: Bebas Neue (section headings, numeric readouts)
- **Mono font**: Share Tech Mono (data fields, codes, specs)
- **Body font**: DM Sans (prose, rationale text)
- **Accent**: Amber `#F59E0B`
- **Stack**: Vite 5 + React 18 + TypeScript 5 + Recharts 3 + motion/react 11

## Views

| Tab | Path | Purpose |
|-----|------|---------|
| Overview | default | Machine profile, 8GB VRAM constraint hero, top upgrade paths, buy/watch/wait signal tiles |
| Component Explorer | — | Filter by category; ranked candidates with specs, compatibility, value/dollar |
| Price & Forecast | — | Per-SKU Recharts time series, ATL marker, seed vs live data, trend + caveats |
| Evidence | — | Citation drawer; every spec/price/compat claim with URL + tier + verification summary |
