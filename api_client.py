import anthropic


class ClaudeClient:
    def __init__(self, model="claude-sonnet-4-6", max_tokens=1000):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def answer(self, query):
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": query}],
        )
        return resp.content[0].text

    def answer_with_context(self, query, context):
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
