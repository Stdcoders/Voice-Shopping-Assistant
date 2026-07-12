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

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB, matches the old multer limit


@app.on_event("startup")
async def on_startup():
    # db's own tables are already initialized elsewhere (existing behavior).
    # This just adds the history table alongside it, in the same DB file,
    # and loads the static product catalog used by search + recommendations.
    history.init_history_table()
    catalog.load_catalog()


@app.get("/health")
async def health():
    return {"status": "ok"}


def _item_name(item: dict) -> str:
    """
    db.get_all_items() rows may key the item name as "name" or "item"
    depending on how db.py shaped it. Try both so recommendations logic
    doesn't silently break if that ever shifts.
    """
    return item.get("name") or item.get("item") or ""


def _needs_item(command: dict) -> bool:
    """
    add/update/remove all require a concrete item name. If the LLM couldn't
    extract one (e.g. "remove everything from the list" — there's no single
    item to resolve), item comes back as None/"" and must not be allowed to
    flow into db.*/history.log_event(), which assume a real string.
    """
    action = command.get("action")
    if action not in ("add", "update", "remove"):
        return False
    item = command.get("item")
    return not item or not str(item).strip()


def apply_command(command: dict):
    """
    Applies a parsed command to the DB, updates the "last command" context for
    resolving future corrections, logs the action to history for the
    recommendations engine, and always returns the current full list.
    """
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
        context.clear_last_command()  # item's gone, nothing sensible to correct anymore
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
        context.clear_last_command()  # list is empty, nothing left to correct
        history.log_event("__all__", action="clear")
        return result_list

    # "list" or "unknown"
    return db.get_all_items()


def handle_search(command: dict) -> List[dict]:
    """
    Search is read-only: it queries the product catalog and never touches
    the shopping list, correction context, or history log.
    """
    category = command.get("category")
    if command.get("item"):
        # The prompt tells the LLM to leave "category" null when a specific
        # item is named (query alone should carry the search), but it
        # doesn't always comply — it sometimes fills in a best-guess category
        # anyway. That gets AND'd with the query filter in catalog.search(),
        # and if the guessed category string doesn't exactly match how the
        # catalog actually categorizes that product, it wrongly excludes
        # real matches (e.g. "toothpaste" + guessed category "household"
        # returning zero results even though toothpaste exists under a
        # different category). Ignoring category whenever a specific item
        # was searched enforces the intended behavior in code.
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