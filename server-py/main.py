import os
from typing import List

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

import db
import context
from transcribe import transcribe_audio
from parse_command import parse_command
import history
import recommendations
import catalog


app = FastAPI(title="Voice Shopping Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  


@app.on_event("startup")
async def on_startup():
    history.init_history_table()
    catalog.load_catalog()


@app.get("/health")
async def health():
    return {"status": "ok"}


def _item_name(item: dict) -> str:
    return item.get("name") or item.get("item") or ""


def _needs_item(command: dict) -> bool:
    action = command.get("action")
    if action not in ("add", "update", "remove"):
        return False
    item = command.get("item")
    return not item or not str(item).strip()


def apply_command(command: dict):
    action = command.get("action")

    if action == "add":
        result_list = db.add_item(command)
        context.set_last_command(command)
        history.log_event(
            command.get("item", ""),
            action="add",
            quantity=command.get("quantity"),
            unit=command.get("unit"),
            category=command.get("category"),
        )
        return result_list

    if action == "update":
        result_list = db.update_item(command)
        context.set_last_command(command)
        history.log_event(
            command.get("item", ""),
            action="update",
            quantity=command.get("quantity"),
            unit=command.get("unit"),
            category=command.get("category"),
        )
        return result_list

    if action == "remove":
        result_list = db.remove_item(command)
        context.clear_last_command()  
        history.log_event(
            command.get("item", ""),
            action="remove",
            quantity=command.get("quantity"),
            unit=command.get("unit"),
            category=command.get("category"),
        )
        return result_list

    if action == "clear":
        result_list = db.clear_list()
        context.clear_last_command()  
        history.log_event("__all__", action="clear")
        return result_list

    return db.get_all_items()


def handle_search(command: dict) -> List[dict]:
    category = command.get("category")
    if command.get("item"):
        category = None

    return catalog.search(
        query=command.get("item"),
        brand=command.get("brand"),
        category=category,
        min_price=command.get("min_price"),
        max_price=command.get("max_price"),
        organic=command.get("organic"),
    )


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
        print(f"[main] parsed command: {command}")
        if command.get("action") == "search":
            results = handle_search(command)
            return {"transcript": transcript, **command, "results": results}

        if _needs_item(command):
            return {
                "transcript": transcript,
                **command,
                "message": "I didn't catch a specific item — try naming it, e.g. \"remove milk\".",
                "list": db.get_all_items(),
            }

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

        if command.get("action") == "search":
            results = handle_search(command)
            return {"transcript": transcript, **command, "results": results}

        if _needs_item(command):
            return {
                "transcript": transcript,
                **command,
                "message": "I didn't catch a specific item — try naming it, e.g. \"remove milk\".",
                "list": db.get_all_items(),
            }

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


@app.get("/api/search")
async def search_products(
    query: str = None,
    brand: str = None,
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    organic: bool = None,
):
    results = catalog.search(
        query=query,
        brand=brand,
        category=category,
        min_price=min_price,
        max_price=max_price,
        organic=organic,
    )
    return {"results": results}


@app.get("/api/recommendations")
async def get_recommendations():
    current_items = [_item_name(item) for item in db.get_all_items()]
    return {"recommendations": recommendations.get_recommendations(current_items)}


@app.post("/api/recommendations/dismiss")
async def dismiss_recommendation(payload: dict = Body(...)):
    item_name = payload.get("item")
    if not item_name or not isinstance(item_name, str):
        raise HTTPException(status_code=400, detail="Expected JSON body: { item: string }")

    recommendations.dismiss_recommendation(item_name)
    return {"status": "dismissed", "item": item_name}