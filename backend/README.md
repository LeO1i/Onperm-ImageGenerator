# OnPrem Image Generator — Backend

Python FastAPI backend for the local image generator described in [docs/BUILD_PLAN.md](../docs/BUILD_PLAN.md).

## Requirements

- Windows 10/11 with NVIDIA GPU (for generation)
- Python 3.11+
- CUDA-enabled PyTorch (install separately for your GPU)

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On Windows with NVIDIA GPU, install PyTorch with CUDA from https://pytorch.org before or after the requirements file.

## Run (development)

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Build the frontend first for the full UI:

```bash
cd frontend
npm install
npm run build
```

The backend serves `frontend/dist/` at `http://127.0.0.1:8000`.

## Windows launcher

From the project root:

- `start.bat` — start backend in background, open browser
- `stop.bat` — stop backend via PID file

## API

All endpoints are under `/api/*`. See `docs/BUILD_PLAN.md` for the full contract.

Key routes:

- `GET /api/health`
- `GET /api/system/preflight`
- `GET /api/models`, `POST /api/models/refresh`
- `GET/POST /api/jobs`, `GET /api/jobs/{id}/events` (SSE)
- `GET/PUT /api/settings`
- `GET/POST /api/prompts/saved`

## Data locations

| Data | Path |
|------|------|
| Settings | `config/settings.json` |
| SQLite DB | `data/app.db` |
| Models | `%APPDATA%/OnPremImageGenerator/models` |
| Thumbnails | `%APPDATA%/OnPremImageGenerator/thumbs` |
| Logs | `%APPDATA%/OnPremImageGenerator/logs` |
