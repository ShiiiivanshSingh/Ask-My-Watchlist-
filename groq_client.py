import os
import requests


class GroqClient:
    def __init__(self, model="llama-3.3-70b-versatile", max_tokens=1000, api_key=None, user_name="Shivansh"):
        self.api_key = api_key or os.environ["GROQ_API_KEY"]
        self.model = model
        self.max_tokens = max_tokens
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.user_name = user_name
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
            f"friend, not like flagging a missing database record."
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