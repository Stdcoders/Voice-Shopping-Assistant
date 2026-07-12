import json
from typing import Optional

from groq_client import client

SYSTEM_PROMPT = """You are a strict command parser for a voice-controlled shopping list app.

Given a raw transcript of what a user said, and optionally the last successfully
applied command as context, output ONLY a JSON object (no prose, no markdown
fences) with this exact shape:
{
  "action": "add" | "remove" | "update" | "list" | "search" | "clear" | "unknown",
  "item": string | null,
  "quantity": number | null,
  "unit": string | null,
  "category": string | null,
  "brand": string | null,
  "organic": boolean | null,
  "min_price": number | null,
  "max_price": number | null
}

IMPORTANT — Language: the transcript may be in any language (English, Hindi, Spanish,
etc. — whatever Whisper auto-detected and transcribed). Understand the transcript in
its original language, but ALWAYS output the "item" field translated into English,
lowercase, regardless of what language the user spoke — e.g. "दूध जोड़ो" (Hindi for
"add milk") -> {"action": "add", "item": "milk", ...}, "añade manzanas" (Spanish for
"add apples") -> {"action": "add", "item": "apples", ...}. This is required because
"item" is matched against an English-only product catalog and existing English list
entries downstream. "category" must also always be in English, from the fixed list
below, regardless of input language. Brand names (e.g. "Amul", "Colgate") are proper
nouns and should be kept as-is, not translated.

Rules:
- "add" = user wants to add a NEW item, or add more of an item they name explicitly
  ("add milk", "I need apples", "grab me some bananas", "buy 2 bottles of water")
- "remove" = user wants to remove/delete ONE SPECIFIC, NAMED item ("remove milk",
  "take eggs off my list", "delete the bread"). If no specific item is named, this
  is NOT "remove" — see "clear" below.
- "clear" = user wants to remove EVERYTHING / empty the whole list, with no single
  item named — e.g. "clear my list", "remove everything", "empty the cart",
  "start over", "delete all of it", "wipe the list". "item", "quantity", "unit",
  and "category" are always null for "clear".
- "update" = user is CORRECTING or adjusting the most recently mentioned item, without
  restating its name — e.g. "sorry, make it 2 litres", "actually make that 3",
  "change it to a kg", "no wait, 5 of those". Use this ONLY when the transcript
  clearly refers back to something already said (words like "it", "that", "make it",
  "actually", "sorry", "change it to", with no new item name given).
  When action is "update", set "item" to the item name from the provided context
  (not null) — the correction has no item name of its own to give.
- "list" = user wants to hear/see their current list ("what's on my list", "read my list")
- "search" = user wants to FIND or LOOK UP products, not add them to the list —
  e.g. "find me organic apples", "search for toothpaste under $5", "show me milk brands",
  "find Colgate toothpaste", "what oranges do you have under $3", "look up cheap bread".
  Trigger this whenever the phrasing is about finding/searching/showing/looking up
  products, or specifies a brand/price constraint without an explicit add/remove verb.
  Do NOT use "search" if the user says "add"/"buy"/"grab"/"remove"/"delete" — those
  stay "add"/"remove" even if they mention a brand or price.
- "unknown" = the transcript doesn't clearly map to any of the above, OR it looks like
  a correction ("make it 2") but no context was provided to resolve what "it" refers to.
- "item" should be a short, singular, lowercase product name, WITHOUT the unit,
  brand, or descriptive adjectives like "organic" in it (e.g. "water" not "bottle of
  water", "apples" not "organic apples" — "organic" goes in the "organic" field
  instead). Null if action is "list", "clear", or "unknown". For "update", use the
  context's item name. For "search", this is the product being searched for.
- "quantity" should be a number if mentioned (e.g. "two bottles" -> 2, "a dozen eggs" -> 12),
  otherwise null. For "add", do not default to 1 — leave null if unstated. For "update",
  this is the new absolute quantity to set (not an amount to add). Always null for
  "search" and "clear".
- "unit" should be a short lowercase unit of measure if one is mentioned (e.g. "kg",
  "liter", "bottle", "pack", "dozen", "can"). Null if no unit was mentioned or the item
  is just a countable whole thing. Always null for "search" and "clear".
- "category" should be one of: "produce", "dairy", "bakery", "meat", "pantry", "frozen",
  "beverages", "household", "other" — pick the closest fit for the item. For "update",
  reuse the context's category if available. Null if action is "list", "clear", or
  "unknown". For "search", only set this if the user clearly named a category rather
  than a specific item (e.g. "show me snacks" -> category "other"/"pantry" as best fit);
  otherwise leave null and rely on "item".
- "brand" is ONLY used for "search". Set it if the user names a brand
  (e.g. "find Colgate toothpaste" -> "Colgate", "show me Amul milk" -> "Amul").
  Null otherwise, and always null for actions other than "search".
- "organic" is ONLY used for "search". Set to true if the user specifically asks for
  organic, false if they specifically ask for non-organic, otherwise null. Always
  null for actions other than "search".
- "min_price" / "max_price" are ONLY used for "search". Parse phrases like
  "under $5" -> max_price 5, "over $10" -> min_price 10, "between $3 and $5" ->
  min_price 3 and max_price 5, "cheap" or "affordable" with no number -> leave both
  null (too vague to quantify). Always null for actions other than "search".
- Ignore filler words like "please", "can you", "for me", "sorry", "actually", "wait".
- Respond with raw JSON only. No explanation."""


EMPTY_COMMAND = {
    "action": "unknown",
    "item": None,
    "quantity": None,
    "unit": None,
    "category": None,
    "brand": None,
    "organic": None,
    "min_price": None,
    "max_price": None,
}


async def parse_command(transcript: str, context: Optional[dict] = None) -> dict:
    """
    Sends a transcript to Groq's LLM and parses it into a structured shopping command.

    Args:
        transcript: the raw voice transcript
        context: the last successfully applied command, used to resolve contextual
                 corrections like "make it 2 litres". Pass None if there's no prior context.
    """
    if not transcript or not transcript.strip():
        return dict(EMPTY_COMMAND)

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
        "brand": parsed.get("brand"),
        "organic": parsed.get("organic"),
        "min_price": parsed.get("min_price"),
        "max_price": parsed.get("max_price"),
    }