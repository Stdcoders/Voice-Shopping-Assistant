# Voice Command Shopping Assistant

A voice-controlled shopping list manager. Users speak commands ("add milk", "remove eggs", "find toothpaste under $5"), and the app transcribes, interprets, and acts on them — while surfacing smart product suggestions based on shopping history.


**Live app:** https://voice-shopping-assistant-teal.vercel.app/
**Backend API:** https://voice-shopping-assistant-erfb.onrender.com ([`/health`](https://voice-shopping-assistant-erfb.onrender.com/health))

---

## Architecture

```
client/       React 18 + Vite frontend (mic capture, list UI, search, recommendations)
server-py/    FastAPI backend (transcription, command parsing, list state, recommendations)
```

**Pipeline:** browser records audio → `POST /api/voice-command` → Groq Whisper (`whisper-large-v3-turbo`) transcribes → Groq Llama (`llama-3.3-70b-versatile`) parses the transcript into a structured command (`action`, `item`, `quantity`, `unit`, `category`, `brand`, `organic`, `min_price`, `max_price`) → command is applied against a SQLite-backed shopping list.

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite |
| Backend | FastAPI, Uvicorn |
| Speech-to-text | Groq Whisper (`whisper-large-v3-turbo`) |
| Command parsing | Groq Llama 3.3 70B (JSON-mode, structured output) |
| Storage | SQLite (`shopping_list.db`, `history` table) |
| Product catalog | Static JSON (`product_catalog.json`) |

---

## Features
```
Voice commands — flexible phrasing ("I need apples" = "add apples"), multilingual input
Smart suggestions — running-low reminders, substitutes, seasonal/on-sale picks, based on your history
List management — add/remove/update items by voice or text
Voice search — find items by name, brand, price range, or category
Simple UI — mic button, live transcript, list, search, and suggestions panel
Multilingual Input - Works on 4 languages : English, Hindi, Marathi and Tamil
```
---


---

## Setup

### Backend (`server-py/`)

```bash
cd server-py
python -m venv env
source env/bin/activate    # Windows: env\Scripts\activate
pip install -r requirements.txt
```

Create `server-py/.env`:
```
GROQ_API_KEY=your_groq_api_key_here
```

Run:
```bash
uvicorn main:app --reload --port 3001
```

### Frontend (`client/`)

```bash
cd client
npm install
npm run dev
```
---

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/voice-command` | Upload audio (`multipart/form-data`, field `audio`) → transcribe → parse → apply |
| `POST` | `/api/parse-text` | Same pipeline, skipping transcription (`{ "transcript": "..." }`) |
| `GET` | `/api/items` | Current shopping list |
| `GET` | `/api/search` | Product search (`query`, `brand`, `category`, `min_price`, `max_price`, `organic`) |
| `GET` | `/api/recommendations` | Current smart suggestions |
| `POST` | `/api/recommendations/dismiss` | Dismiss/snooze a suggested item (`{ "item": "..." }`) |

---
