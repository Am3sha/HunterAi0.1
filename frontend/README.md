# HunterAI Frontend

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui.

Sprint 0 scope: enter a domain → start a scan → poll status → display subdomains,
live HTTP services, and endpoints. No auth.

## Architecture

```
src/
  app/
    layout.tsx          root layout
    page.tsx            workflow page (composes the hook + components)
    globals.css         Tailwind + shadcn theme tokens
  lib/
    types.ts            types mirroring the backend API
    api.ts              typed HTTP client (createScan, getScan)
    utils.ts            cn() helper
  hooks/
    use-scan.ts         create → poll → terminal state machine
  components/
    ui/                 shadcn primitives (button, input, card, badge, table)
    scan/               feature components (form, status, results, tables)
```

Layering: components and the hook depend on `lib/api` + `lib/types`; only
`lib/api` knows the backend URLs. New result types or sections are added under
`components/scan/` without touching the API/hook.

## Run (inside WSL / Linux)

```bash
cd frontend
cp .env.local.example .env.local      # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                           # http://localhost:3000
```

The backend must be running (see `../backend/README.md`) and its CORS origins
must include `http://localhost:3000` (default).

## Adding shadcn/ui components

`components.json` is configured, so you can extend with e.g.:

```bash
npx shadcn@latest add dialog
```
