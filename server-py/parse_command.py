import json
from typing import Optional

from groq_client import client

SYSTEM_PROMPT = """You are a strict command parser for a voice-controlled shopping list app.

Given a raw transcript of what a user said, and optionally the last successfully
applied command as context, output ONLY a JSON object (no prose, no markdown
fences) with this exact shape:
{
  "action": "add" | "remove" | "update" | "list" | "unknown",
  "item": string | null,
  "quantity": number | null,
  "unit": string | null,
  "category": string | null
}

Rules:
- "add" = user wants to add a NEW item, or add more of an item they name explicitly
  ("add milk", "I need apples", "grab me some bananas", "buy 2 bottles of water")
- "remove" = user wants to remove/delete an item ("remove milk", "take eggs off my list", "delete the bread")
- "update" = user is CORRECTING or adjusting the most recently mentioned item, without
  restating its name — e.g. "sorry, make it 2 litres", "actually make that 3",
  "change it to a kg", "no wait, 5 of those". Use this ONLY when the transcript
  clearly refers back to something already said (words like "it", "that", "make it",
  "actually", "sorry", "change it to", with no new item name given).
  When action is "update", set "item" to the item name from the provided context
  (not null) — the correction has no item name of its own to give.
- "list" = user wants to hear/see their current list ("what's on my list", "read my list")
- "unknown" = the transcript doesn't clearly map to any of the above, OR it looks like
  a correction ("make it 2") but no context was provided to resolve what "it" refers to.
- "item" should be a short, singular, lowercase product name, WITHOUT the unit in it
  (e.g. "water" not "bottle of water", "rice" not "kg of rice"). Null if action is
  "list" or "unknown". For "update", use the context's item name.
- "quantity" should be a number if mentioned (e.g. "two bottles" -> 2, "a dozen eggs" -> 12),
  otherwise null. For "add", do not default to 1 — leave null if unstated. For "update",
  this is the new absolute quantity to set (not an amount to add).
- "unit" should be a short lowercase unit of measure if one is mentioned (e.g. "kg",
  "liter", "bottle", "pack", "dozen", "can"). Null if no unit was mentioned or the item
  is just a countable whole thing.
- "category" should be one of: "produce", "dairy", "bakery", "meat", "pantry", "frozen",
  "beverages", "household", "other" — pick the closest fit for the item. For "update",
  reuse the context's category if available. Null if action is "list" or "unknown".
- Ignore filler words like "please", "can you", "for me", "sorry", "actually", "wait".
- Respond with raw JSON only. No explanation."""


async def parse_command(transcript: str, context: Optional[dict] = None) -> dict:
    """
    Sends a transcript to Groq's LLM and parses it into a structured shopping command.

    Args:
        transcript: the raw voice transcript
        context: the last successfully applied command, used to resolve contextual
                 corrections like "make it 2 litres". Pass None if there's no prior context.
    """
    empty = {"action": "unknown", "item": None, "quantity": None, "unit": None, "category": None}

    if not transcript or not transcript.strip():
        return empty

    if context:
        user_content = f'Previous command context: {json.dumps(context)}\n\nCurrent transcript: "{transcript}"'
    else:
        user_content = f'Current transcript: "{transcript}"'

    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw = completion.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    return {
        "action": parsed.get("action") or "unknown",
        "item": parsed.get("item"),
        "quantity": parsed.get("quantity"),
        "unit": parsed.get("unit"),
        "category": parsed.get("category"),
    }