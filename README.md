# Energent

AI-powered Building Energy Optimization Platform. Runs EnergyPlus simulations, analyzes energy consumption, and generates optimization recommendations using rule-based analysis and LLM-powered refinement.

## Architecture

```
React Frontend (Vite + Tailwind)
        ↓
    FastAPI Backend
        ↓
   Service Layer
   ├── EnergyPlus Runner  →  Execute simulations
   ├── CSV Parser         →  Parse simulation output
   ├── Analysis Engine    →  Energy breakdown, peak load, recommendations
   └── LLM Provider       →  OpenRouter/Qwen refinement
```

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic, Pandas
- **Frontend:** React, Vite, Tailwind CSS, Recharts
- **Simulation:** EnergyPlus
- **AI:** OpenRouter (Qwen model), with provider abstraction for swapping

## Prerequisites

- Python 3.12+
- Node.js 18+
- EnergyPlus installed ([download](https://energyplus.net/))

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd energent
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your paths:
- `ENERGYPLUS_EXE_PATH` — path to your EnergyPlus executable
- `OPENROUTER_API_KEY` — your OpenRouter API key (optional, for LLM features)

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
python run.py
```

Backend runs at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/simulation/run` | Run EnergyPlus simulation + analysis |
| POST | `/api/llm/refine` | Refine recommendations with LLM |
| POST | `/api/llm/ask` | Ask questions about building energy |
| GET | `/api/llm/health` | Check LLM provider status |

## Project Structure

```
energent/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers
│   │   ├── services/       # Business logic
│   │   │   ├── energyplus/ # Simulation runner + parser
│   │   │   ├── analysis/   # Energy analysis engine
│   │   │   └── llm/        # LLM provider abstraction
│   │   ├── config.py       # Pydantic settings
│   │   ├── constants.py    # Shared constants
│   │   └── main.py         # App factory
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route pages
│   │   ├── api.js          # API client
│   │   └── App.jsx         # Router setup
│   └── package.json
└── simulation/
    ├── idf/                # EnergyPlus building models
    └── weather/            # Weather files
```

## Usage

1. Open `http://localhost:5173`
2. Click **Run Simulation** on the Dashboard or Simulation page
3. View results on the Results page with energy breakdown charts
4. Click **AI Refine** to get LLM-enhanced recommendations (requires API key)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Energent | Application name |
| `APP_VERSION` | 0.1.0 | Application version |
| `DEBUG` | false | Debug mode |
| `LOG_LEVEL` | INFO | Logging level |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `ENERGYPLUS_EXE_PATH` | — | Path to EnergyPlus executable |
| `ENERGYPLUS_IDF_PATH` | — | Path to .idf building model |
| `ENERGYPLUS_WEATHER_PATH` | — | Path to .epw weather file |
| `ENERGYPLUS_OUTPUT_DIR` | — | Simulation output directory |
| `ENERGYPLUS_TIMEOUT` | 600 | Simulation timeout (seconds) |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `OPENROUTER_MODEL` | qwen/qwen3-8b | LLM model name |
| `LLM_TIMEOUT` | 60 | LLM API timeout (seconds) |
