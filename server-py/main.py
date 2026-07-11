import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

import db
import context
from transcribe import transcribe_audio
from parse_command import parse_command

app = FastAPI(title="Voice Shopping Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB, matches the old multer limit


@app.get("/health")
async def health():
    return {"status": "ok"}


def apply_command(command: dict):
    """
    Applies a parsed command to the DB, updates the "last command" context for
    resolving future corrections, and always returns the current full list.
    """
    action = command.get("action")

    if action == "add":
        result_list = db.add_item(command)
        context.set_last_command(command)
        return result_list

    if action == "update":
        result_list = db.update_item(command)
        context.set_last_command(command)
        return result_list

    if action == "remove":
        result_list = db.remove_item(command)
        context.clear_last_command()  # item's gone, nothing sensible to correct anymore
        return result_list

    # "list" or "unknown"
    return db.get_all_items()


@app.post("/api/voice-command")
async def voice_command(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="No audio file received. Expected a multipart field named 'audio'.",
        )

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Audio file too large (max 10MB).")

    try:
        transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")

        if not transcript:
            return {
                "transcript": "",
                "action": "unknown",
                "item": None,
                "quantity": None,
                "message": "Didn't catch any speech in that clip. Try again.",
                "list": db.get_all_items(),
            }

        command = await parse_command(transcript, context.get_last_command())
        result_list = apply_command(command)

        return {"transcript": transcript, **command, "list": result_list}
    except HTTPException:
        raise
    except Exception as err:
        print(f"[voice-command] failed: {err}")
        raise HTTPException(
            status_code=502, detail="Voice processing failed. Please try again."
        )


@app.post("/api/parse-text")
async def parse_text(payload: dict = Body(...)):
    transcript = payload.get("transcript")

    if not transcript or not isinstance(transcript, str):
        raise HTTPException(
            status_code=400, detail="Expected JSON body: { transcript: string }"
        )

    try:
        command = await parse_command(transcript, context.get_last_command())
        result_list = apply_command(command)
        return {"transcript": transcript, **command, "list": result_list}
    except Exception as err:
        print(f"[parse-text] failed: {err}")
        raise HTTPException(
            status_code=502, detail="Command parsing failed. Please try again."
        )


@app.get("/api/items")
async def get_items():
    return {"list": db.get_all_items()}