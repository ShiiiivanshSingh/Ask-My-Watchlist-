import re
import difflib


# Words that signal the user wants *every* entry in a series, not just one.
FRANCHISE_WORDS = {"trilogy", "series", "franchise", "saga", "movies", "films",
                    "duology", "quadrilogy", "collection"}

# Words with no identifying power on their own. A bare span made up only of
# these (e.g. "my", "them", "have i") must never be fuzzy-matched against a
# movie title -- that's how "my" ended up matching "May" at a higher score
# than "godafther" matched "The Godfather".
QUERY_NOISE_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "how", "when",
    "where", "who", "which", "of", "to", "in", "on", "for", "and", "or",
    "our", "it", "its", "be", "do", "does", "did", "have", "has", "having",
    "i", "my", "me", "you", "your", "he", "she", "they", "them", "this",
    "that", "think", "seen", "watch", "watched", "rate", "rated", "rating",
    "review", "like", "liked", "about", "if", "not",
}


# Signals a query wants the extreme LOW end of your ratings (worst/least-liked).
RATING_LOW_WORDS = {"least", "lowest", "worst", "dislik", "hate", "hated", "bad", "disliked"}
# Signals the extreme HIGH end (favorite/best-liked). "most" alone is
# ambiguous ("disliked the most" is LOW) so it only counts here when a
# low-signal word isn't also present -- checked in _rating_direction.
RATING_HIGH_WORDS = {"favorite", "favourite", "best", "highest", "love", "loved", "most", "top"}


class MovieKB:
    def __init__(self, name_to_chunk, match_threshold=0.8):
        self.entries = [(name, chunk) for name, chunk in name_to_chunk.items()]
        self.match_threshold = match_threshold

    @staticmethod
    def _norm(name):
        return re.sub(r"^(the|a|an)\s+", "", name.lower()).strip()

    def _franchise_group(self, name):
        """All entries that are the same base title or a numbered/subtitled
        extension of it -- 'Cars' -> Cars, Cars 2, Cars 3; 'The Godfather' ->
        The Godfather, The Godfather Part II, The Godfather Part III."""
        base = self._norm(name)
        group = []
        for other_name, other_chunk in self.entries:
            other_norm = self._norm(other_name)
            if (other_norm == base
                    or other_norm.startswith(base + " ")
                    or base.startswith(other_norm + " ")):
                group.append((other_name, other_chunk))
        return group

    @staticmethod
    def _wants_franchise(q_lower):
        words = re.findall(r"[a-z']+", q_lower)
        for w in words:
            if w in FRANCHISE_WORDS:
                return True
            if len(w) > 3:
                for fw in FRANCHISE_WORDS:
                    if difflib.SequenceMatcher(None, w, fw).ratio() >= 0.8:
                        return True
        return False

    @staticmethod
    def _rating_direction(q_lower):
        """None if this isn't a superlative-rating question. 'low' for
        worst/least-liked, 'high' for best/favorite. Dislike-style words
        win over a bare 'most' -- 'disliked the most' is still LOW."""
        if any(w in q_lower for w in RATING_LOW_WORDS):
            return "low"
        if any(w in q_lower for w in RATING_HIGH_WORDS):
            return "high"
        return None

    def _extract_ratings(self):
        """{movie_name: most_recent_numeric_rating} for every per-movie
        entry that has one -- skips watchlist-only entries, unrated
        entries, and non-movie extras like the profile/comments chunks."""
        ratings = {}
        for name, chunk in self.entries:
            if not chunk.startswith("Movie:"):
                continue
            found = re.findall(r"Rating:\s*(\d+(?:\.\d+)?)/5", chunk)
            if found:
                ratings[name] = float(found[-1])  # last = most recent watch
        return ratings

    def _resolve_superlative(self, direction, max_tied=8):
        ratings = self._extract_ratings()
        if not ratings:
            return None, 0.0
        target = min(ratings.values()) if direction == "low" else max(ratings.values())
        tied = [name for name, r in ratings.items() if r == target]
        chunks_by_name = dict(self.entries)
        shown = tied[:max_tied]
        combined = "\n\n".join(chunks_by_name[n] for n in shown)
        if len(tied) > max_tied:
            combined += (
                f"\n\n(Note: {len(tied)} movies are tied at this rating -- "
                f"showing {max_tied} of them.)"
            )
        return combined, 1.0

    def _candidates(self, query):
        words = re.findall(r"[a-zA-Z0-9']+", query)
        spans = []
        for size in (6, 5, 4, 3, 2, 1):
            for i in range(len(words) - size + 1):
                span_words = words[i:i + size]
                has_content = any(
                    w.lower() not in QUERY_NOISE_WORDS and len(w) > 2
                    for w in span_words
                )
                if not has_content:
                    continue
                spans.append(" ".join(span_words))
        return spans

    def _resolve(self, name, score, wants_franchise):
        if wants_franchise:
            group = self._franchise_group(name)
            if len(group) > 1:
                combined = "\n\n".join(chunk for _, chunk in group)
                return combined, score
        for n, chunk in self.entries:
            if n == name:
                return chunk, score
        return None, score

    def query(self, question, top_k=1):
        q_lower = question.lower()
        wants_franchise = self._wants_franchise(q_lower)

        exact_matches = [
            (name, chunk) for name, chunk in sorted(self.entries, key=lambda e: -len(e[0]))
            if re.search(r"\b" + re.escape(name.lower()) + r"\b", q_lower)
        ]
        if exact_matches:
            best_name, best_chunk = exact_matches[0]
            resolved, score = self._resolve(best_name, 1.0, wants_franchise)
            return (resolved or best_chunk), score

        # No literal movie title in the question -- check whether it's
        # asking for an extreme across the whole log (lowest/highest rated)
        # rather than a single title, which the fuzzy matcher below can't
        # answer since there's no name to match against.
        direction = self._rating_direction(q_lower)
        if direction:
            resolved, score = self._resolve_superlative(direction)
            if resolved:
                return resolved, score

        best_score, best_name = 0.0, None
        for span in self._candidates(question):
            for name, _ in self.entries:
                norm_name = self._norm(name)
                if len(norm_name) < 4:
                    continue  # too short to typo-match reliably (e.g. "bio" ~ "IO")
                score = difflib.SequenceMatcher(None, span.lower(), norm_name).ratio()
                if score > best_score:
                    best_score, best_name = score, name

        if best_score >= self.match_threshold:
            resolved, score = self._resolve(best_name, best_score, wants_franchise)
            return resolved, score
        return None, best_score


def build_movie_kb(chunks, extra_entries=None):
    """extra_entries is an optional {name: chunk} dict for non-movie KB
    entries (e.g. profile info, comments) that don't follow the
    'Movie: Name (Year)' chunk format."""
    name_to_chunk = {}
    for chunk in chunks:
        first_line = chunk.split("\n", 1)[0]
        name = first_line[len("Movie: "):].rsplit(" (", 1)[0]
        name_to_chunk[name] = chunk
    if extra_entries:
        name_to_chunk.update(extra_entries)
    return MovieKB(name_to_chunk)