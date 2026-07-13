import csv
from collections import defaultdict


def _read_rows(path):
    if path is None:
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_letterboxd_kb(reviews_path, watched_path, ratings_path=None,
                        diary_path=None, watchlist_path=None):
    """Builds one text chunk per watched movie, folding in every rating
    source available (reviews, dedicated ratings export, diary) so a movie
    that was only ever rated -- never reviewed -- still shows its score
    instead of falling back to 'no rating given'. Also returns a chunk per
    watchlist movie (not yet watched) so those are queryable too.
    """
    reviews = defaultdict(list)
    for row in _read_rows(reviews_path):
        reviews[(row["Name"], row["Year"])].append(row)

    watched = {}
    for row in _read_rows(watched_path):
        key = (row["Name"], row["Year"])
        if key not in watched:
            watched[key] = row["Date"]

    # ratings.csv / diary.csv both carry a Rating for movies that may not
    # have an accompanying written review.
    ratings_map = {}
    for row in _read_rows(ratings_path):
        if row.get("Rating"):
            ratings_map[(row["Name"], row["Year"])] = row["Rating"]
    for row in _read_rows(diary_path):
        key = (row["Name"], row["Year"])
        if row.get("Rating") and key not in ratings_map:
            ratings_map[key] = row["Rating"]

    all_keys = set(reviews) | set(watched) | set(ratings_map)
    chunks = []
    for name, year in all_keys:
        key = (name, year)
        entries = reviews.get(key, [])
        lines = [f"Movie: {name} ({year})"]

        if entries:
            for e in sorted(entries, key=lambda r: r["Watched Date"] or r["Date"]):
                rewatch = " (rewatch)" if e["Rewatch"] == "Yes" else ""
                rating = f"{e['Rating']}/5" if e["Rating"] else "no rating given"
                watched_date = e["Watched Date"] or e["Date"]
                line = f"Watched on {watched_date}{rewatch}. Rating: {rating}."
                if e["Review"]:
                    line += f" Review: {e['Review']}"
                lines.append(line)
        elif key in watched:
            rating = ratings_map.get(key)
            rating_str = f"Rating: {rating}/5. No review written." if rating else "No rating or review given."
            lines.append(f"Watched on {watched[key]}. {rating_str}")
        else:
            # Rated via ratings.csv/diary.csv but not present in watched.csv
            # or reviews.csv -- still worth surfacing.
            lines.append(f"Rating: {ratings_map[key]}/5. No watch date or review on file.")

        chunks.append("\n".join(lines))

    watchlist_chunks = []
    if watchlist_path:
        watched_or_rated = set(reviews) | set(watched) | set(ratings_map)
        for row in _read_rows(watchlist_path):
            key = (row["Name"], row["Year"])
            if key in watched_or_rated:
                continue
            watchlist_chunks.append(
                f"Movie: {row['Name']} ({row['Year']})\n"
                f"On watchlist, not yet watched. Added to watchlist on {row['Date']}."
            )

    return chunks + watchlist_chunks


def load_profile_chunk(profile_path):
    rows = _read_rows(profile_path)
    if not rows:
        return None
    p = rows[0]
    lines = ["Letterboxd profile"]
    if p.get("Username"):
        lines.append(f"Username: {p['Username']}")
    if p.get("Given Name") or p.get("Family Name"):
        lines.append(f"Name: {p.get('Given Name', '')} {p.get('Family Name', '')}".strip())
    if p.get("Date Joined"):
        lines.append(f"Joined Letterboxd on {p['Date Joined']}.")
    if p.get("Location"):
        lines.append(f"Location: {p['Location']}")
    if p.get("Pronoun"):
        lines.append(f"Pronoun: {p['Pronoun']}")
    if p.get("Bio"):
        lines.append(f"Bio: {p['Bio']}")
    if p.get("Favorite Films"):
        lines.append(f"Favorite films (Letterboxd links): {p['Favorite Films']}")
    return "\n".join(lines)


def load_comments_chunk(comments_path):
    rows = _read_rows(comments_path)
    if not rows:
        return None
    lines = ["Comments left on other Letterboxd reviews"]
    for row in sorted(rows, key=lambda r: r["Date"]):
        lines.append(f"On {row['Date']} (re: {row['Content']}): {row['Comment']}")
    return "\n".join(lines)


if __name__ == "__main__":
    chunks = load_letterboxd_kb(
        "/mnt/user-data/uploads/reviews.csv",
        "/mnt/user-data/uploads/watched.csv",
        ratings_path="/mnt/user-data/uploads/ratings.csv",
        diary_path="/mnt/user-data/uploads/diary.csv",
        watchlist_path="/mnt/user-data/uploads/watchlist.csv",
    )
    print(len(chunks), "movie/watchlist entries loaded")
    print(chunks[0])