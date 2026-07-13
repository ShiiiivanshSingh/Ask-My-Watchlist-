from pipeline import Pipeline
from api_client import ClaudeClient

pipeline = Pipeline(api_client=ClaudeClient())

pipeline.add_knowledge("""
Our refund policy allows returns within 30 days of purchase.
Items must be unused and in original packaging.
Refunds are processed within 5 business days after we receive the item.
""")

result1 = pipeline.ask("What is the refund window?")
print(result1)

result2 = pipeline.ask("How long is the refund period?")
print(result2)

result3 = pipeline.ask("What's the capital of France?")
print(result3)
