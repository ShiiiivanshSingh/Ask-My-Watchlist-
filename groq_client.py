import csv
import os
import requests

# Paths to instruction files (relative to this file's directory)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOP20_CSV = os.path.join(_BASE_DIR, "data", "lists", "my-top-20-ranked.csv")
_TASTE_TXT = os.path.join(_BASE_DIR, "data", "lists", "opo.txt")


def _load_top20(path: str) -> str:
    """Parse the Letterboxd list CSV and return a ranked list as a string."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            lines = f.readlines()
        # Find the row that starts the ranked entries (after "Position,Name,...")
        start = next(i for i, l in enumerate(lines) if l.startswith("Position,"))
        reader = csv.DictReader(lines[start:])
        entries = [f"{row['Position']}. {row['Name']} ({row['Year']})" for row in reader if row.get("Position")]
        return "\n".join(entries)
    except Exception:
        return "(top 20 list unavailable)"


def _load_taste_profile(path: str) -> str:
    """Read the plain-text taste profile file."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "(taste profile unavailable)"


class GroqClient:
    def __init__(self, model="llama-3.3-70b-versatile", max_tokens=1000, api_key=None, user_name="Shivansh"):
        self.api_key = api_key or os.environ["GROQ_API_KEY"]
        self.model = model
        self.max_tokens = max_tokens
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.user_name = user_name

        top20 = _load_top20(_TOP20_CSV)
        taste = _load_taste_profile(_TASTE_TXT)

        self.system_prompt = (
            f"You are a warm, personal companion who knows {user_name}'s movie diary "
            f"inside and out -- reviews, ratings, watchlist, diary entries, the lot. "
            f"Talk like a close friend who's read every entry, not like a database "
            f"summarizing records. Always refer to {user_name} by name in the third "
            f"person rather than saying 'you' or 'your' -- for example, "
            f"\"{user_name}'s favorite movie is...\" instead of \"your favorite movie is...\". "
            f"Avoid stiff, clinical phrasing like 'according to the provided context' or "
            f"'there is no indication that' -- instead write the way someone would talk "
            f"about a friend's taste in film: with warmth, specificity, and a little "
            f"personality. Lean into the actual feelings and reactions {user_name} wrote "
            f"down rather than just restating facts. If {user_name} hasn't seen or "
            f"reviewed something, say so simply and kindly, like catching up an old "
            f"friend, no em dashes in response, not like flagging a missing database record."
            f"\n\n"
            f"{user_name}'s definitive personal top 20 ranked films (in order) are:\n"
            f"{top20}\n"
            f"Whenever {user_name} or anyone asks about {user_name}'s top 5, top 10, or top 20 "
            f"movies/films, always use this list as the definitive ranked source."
            f"\n\n"
            f"{taste}"
        )

    def _call(self, messages):
        resp = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def answer(self, query):
        return self._call([{"role": "user", "content": query}])

    def answer_with_context(self, query, context):
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
        return self._call([{"role": "user", "content": prompt}])