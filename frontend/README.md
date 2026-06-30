# OnPrem Image Generator — Frontend

React + TypeScript UI for the local image generator described in [docs/BUILD_PLAN.md](../docs/BUILD_PLAN.md).

## Stack

- **Vite** + **React 19** + **TypeScript**
- **React Router** for navigation
- Code-split **History** and **Settings** pages (`React.lazy`)

## Development

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`. Start the FastAPI backend separately for full functionality.

## Production build

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`. The FastAPI backend serves these static files in production at `http://127.0.0.1:8000`.

## Pages

| Route | Feature |
|-------|---------|
| `/` | Generate — model dropdown, prompts, size presets, SSE progress, gallery |
| `/prompts` | Saved prompt library (search, favorites, CRUD) |
| `/history` | Job history with detail view and "Use again" |
| `/settings` | Output directory, retention, system status / preflight |

## API integration

All API calls use relative paths under `/api/*` as defined in the build plan. The frontend expects the backend to be running on the same origin (port 8000 in production).
