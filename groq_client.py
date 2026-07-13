import os
import requests


class GroqClient:
    def __init__(self, model="llama-3.3-70b-versatile", max_tokens=1000, api_key=None):
        self.api_key = api_key or os.environ["GROQ_API_KEY"]
        self.model = model
        self.max_tokens = max_tokens
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def _call(self, messages):
        resp = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def answer(self, query):
        return self._call([{"role": "user", "content": query}])

    def answer_with_context(self, query, context):
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
        return self._call([{"role": "user", "content": prompt}])