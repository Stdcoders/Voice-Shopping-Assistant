import os
from groq import AsyncGroq

if not os.environ.get("GROQ_API_KEY"):
    print(
        "[groq_client] GROQ_API_KEY is not set. Requests to Groq will fail "
        "until you add it to your .env file."
    )

client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))