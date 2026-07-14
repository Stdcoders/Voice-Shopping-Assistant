# Voice Command Shopping Assistant

A voice-controlled shopping list manager. 
Users speak commands ("add milk", "remove eggs", "find toothpaste under $5"), and the app transcribes, interprets, and acts on them — while surfacing smart product suggestions based on shopping history.

# Live URL 
Live app: https://voice-shopping-assistant-teal.vercel.app/
Backend API: https://voice-shopping-assistant-erfb.onrender.com (/health)

# To be noted 

The backend service - Render is on free tier. It's instances spin down after inactivity, so the SQLite Database will get reset on reploy or restart.

# Architecture

client/       React 18 + Vite frontend (mic capture, list UI, search, recommendations)
server-py/    FastAPI backend (transcription, command parsing, list state, recommendations)

# Pipeline

Browser records audio → POST /api/voice-command → Groq Whisper (whisper-large-v3-turbo) transcribes → Groq Llama (llama-3.3-70b-versatile) parses the transcript into a structured command (action, item, quantity, unit, category, brand, organic, min_price, max_price) → command is applied against a SQLite-backed shopping list.

# Features 


# Setup
Backend (server-py/)

cd server-py
python -m venv env
source env/bin/activate    # Windows: env\Scripts\activate
pip install -r requirements.txt

.env -> GROQ_API_KEY=your_groq_api_key_here

Run Command -> uvicorn main:app --reload --port 3001

Frontend (client/)

cd client
npm install
npm run dev

# API Reference

GET | /health | Health check
POST | /api/voice-command| Upload audio (multipart/form-data, field audio) → transcribe → parse → apply
POST | /api/parse-text| Same pipeline, skipping transcription ({ "transcript": "..." })
GET | /api/items | Current shopping list
GET | /api/search | Product search (query, brand, category, min_price, max_price, organic)
GET | /api/recommendations | Current smart suggestions
POST | /api/recommendations/dismiss | Dismiss/snooze a suggested item ({ "item": "..." })
