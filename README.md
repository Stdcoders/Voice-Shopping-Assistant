# Voice Command Shopping Assistant

A voice-controlled shopping list manager. 
Users speak commands ("add milk", "remove eggs", "find toothpaste under $5"), and the app transcribes, interprets, and acts on them — while surfacing smart product suggestions based on shopping history.

# Architecture

client/       React 18 + Vite frontend (mic capture, list UI, search, recommendations)
server-py/    FastAPI backend (transcription, command parsing, list state, recommendations)

# Pipeline

Browser records audio → POST /api/voice-command → Groq Whisper (whisper-large-v3-turbo) transcribes → Groq Llama (llama-3.3-70b-versatile) parses the transcript into a structured command (action, item, quantity, unit, category, brand, organic, min_price, max_price) → command is applied against a SQLite-backed shopping list.
