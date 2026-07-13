from flask import Flask, request, jsonify, render_template

from pipeline import Pipeline
from groq_client import GroqClient
from movie_loader import load_letterboxd_kb, load_profile_chunk, load_comments_chunk
from movie_kb import build_movie_kb

app = Flask(__name__)

pipeline = Pipeline(api_client=GroqClient(), cache_threshold=0.85, store_dir="store_shelf")

chunks = load_letterboxd_kb(
    "data/reviews.csv", "data/watched.csv",
    ratings_path="data/ratings.csv",
    diary_path="data/diary.csv",
    watchlist_path="data/watchlist.csv",
)

extra_entries = {}
profile_chunk = load_profile_chunk("data/profile.csv")
if profile_chunk:
    extra_entries["My Profile"] = profile_chunk
comments_chunk = load_comments_chunk("data/comments.csv")
if comments_chunk:
    extra_entries["My Comments"] = comments_chunk

pipeline.kb = build_movie_kb(chunks, extra_entries=extra_entries)
print(f"loaded {len(chunks)} movie/watchlist entries, {len(extra_entries)} extra entries")


@app.route("/")
def index():
    return render_template("index.html", movie_count=len(chunks))


@app.route("/ask", methods=["POST"])
def ask():
    query = request.json.get("query", "").strip()
    if not query:
        return jsonify({"error": "empty query"}), 400
    result = pipeline.ask(query)
    return jsonify(result)


@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    cleared = pipeline.clear_cache()
    return jsonify({"cleared": cleared, "cache_size": pipeline.cache_size()})


@app.route("/stats")
def stats():
    return jsonify({"cache_size": pipeline.cache_size(), "movie_count": len(chunks)})


if __name__ == "__main__":
    app.run(debug=True, port=5050)