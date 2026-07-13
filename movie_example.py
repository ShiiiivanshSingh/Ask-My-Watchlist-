from pipeline import Pipeline
from groq_client import GroqClient
from movie_loader import load_letterboxd_kb
from movie_kb import build_movie_kb

pipeline = Pipeline(api_client=GroqClient(), cache_threshold=0.55)

chunks = load_letterboxd_kb("reviews.csv", "watched.csv")
pipeline.kb = build_movie_kb(chunks)

print(pipeline.ask("What did I think of Magnolia?"))
print(pipeline.ask("Have I watched Parasite?"))
print(pipeline.ask("Did I like The Thing?"))
print(pipeline.ask("How did I rate Incendies?"))
