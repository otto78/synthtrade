# ⚡ SynthTrade

> *Synthetic intelligence. Real profits.*

Piattaforma di trading algoritmico crypto con AI. Genera, backtesta e valuta strategie automaticamente, eseguendole in paper trading (e live in futuro).

---

## Stack

- **Backend:** FastAPI + Supabase (PostgreSQL) + ccxt (Binance)
- **Frontend:** Angular 17+ (dark terminal UI)
- **AI:** cascade OpenRouter (4 modelli free + fallback Claude Haiku)
- **Infra:** Docker + Supabase CLI

---

## Setup locale

### Prerequisiti

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Supabase CLI (`npm install -g supabase`)

### 1. Backend

```bash
cd synthtrade/backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Compila .env con le tue chiavi
```

### 2. Supabase locale

```bash
cd synthtrade/supabase
supabase start
supabase db reset   # applica migrations + seed
```

### 3. Avvia backend

```bash
cd synthtrade/backend
uvicorn app.main:app --reload --port 8008
# http://localhost:8008/health
```

### 4. Frontend

```bash
cd synthtrade/frontend/synthtrade-ui
npm install
npm start
# http://localhost:4208
```

### 5. Docker (alternativa)

```bash
docker-compose up --build
```

---

## Test

```bash
cd synthtrade/backend
pytest
```

---

## Struttura

```
synthtrade/
├── backend/        FastAPI app
├── frontend/       Angular app
├── supabase/       Migrations + config
└── docker-compose.yml
```
