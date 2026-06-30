# OnPrem Image Generator

Windows-only local web app for text-to-image generation with NVIDIA CUDA, built per [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md).

## Quick start (Windows)

1. Install Python 3.11+ and Node.js
2. Install CUDA-enabled PyTorch for your GPU
3. Setup backend:
   ```bat
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Build frontend:
   ```bat
   cd frontend
   npm install
   npm run build
   ```
5. Double-click **`start.bat`** at the project root

The app opens at **http://127.0.0.1:8000**. Use **`stop.bat`** to shut down the backend.

## Project layout

- `backend/` — FastAPI API, SQLite, Diffusers generation worker
- `frontend/` — React UI
- `config/settings.json` — user settings (created on first run)
- `data/app.db` — prompt library and job history
- `start.bat` / `stop.bat` — Windows launcher scripts

## Development

Run backend and frontend separately:

```bash
# Terminal 1
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2
cd frontend && npm run dev
```

Vite proxies `/api` to port 8000 during development.
