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

**Voice input**
- Voice command recognition via Groq Whisper, with free-form phrasing handled by the LLM parser rather than fixed keyword matching (e.g. "I want to buy bananas" and "add bananas" both resolve to the same `add` command).
- Multilingual input: Whisper auto-detects the spoken language and transcribes it; the parser prompt explicitly instructs the LLM to understand the transcript in its original language and always translate the extracted `item`/`category` fields into English (needed since they're matched against an English-only catalog). Brand names are kept as-is.
- Context-aware corrections: a lightweight in-memory `context` module remembers the last applied command so follow-ups like "make it 2 litres" resolve without repeating the item name.

**Smart suggestions** (`recommendations.py`)
- *Running low*: flags items the user has added at least twice before, once the time since the last add exceeds ~80% of their historical average gap.
- *Substitutes*: for items already on the list, surfaces catalog-defined alternatives (e.g. milk → almond/oat/soy milk).
- *Seasonal / on sale*: pulls from the product catalog's `in_season_months` and `on_sale` fields.
- *Frequently bought together*: co-occurrence of items added on the same day.
- *Cold start*: falls back to a fixed staples list (milk, bread, eggs, bananas, rice) until there's enough history (5+ add events).
- Suggestions can be dismissed, which snoozes that item for 3 days.

**Shopping list management**
- Add / remove / update / clear, all voice- or text-driven, with quantity accumulation (adding "milk" twice sums quantities rather than duplicating rows) and simple singular/plural name matching.

**Voice-activated search**
- Search by item name, brand, category, price range (`min_price`/`max_price` parsed from phrases like "under $5"), and organic flag, run against the local product catalog.

**UI/UX**
- Minimal React interface: mic button, live transcript display, shopping list, search panel, recommendations panel.
- Basic error handling: oversized/empty audio, failed transcriptions, and failed parses return descriptive errors instead of silent failures.

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

By default the Vite dev server proxies API calls to `localhost:3001`. For a production build pointing at the deployed backend, set `VITE_API_URL` (no trailing slash) before building — this is how the live Vercel deployment is configured:
```bash
VITE_API_URL=https://voice-shopping-assistant-erfb.onrender.com npm run build
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

*(~155 words)*
