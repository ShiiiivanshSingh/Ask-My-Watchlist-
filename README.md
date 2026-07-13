<div align="center">

# Ask Shelf!


<div align="center">
  <a href="https://ask-my-watchlist.vercel.app/" target="_blank">
    <img src="https://img.shields.io/badge/Live_on_Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live on Vercel" />
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://ask-my-watchlist.onrender.com/" target="_blank">
    <img src="https://img.shields.io/badge/Live_on_Render-46E3B7?style=for-the-badge&logo=render&logoColor=black" alt="Live on Render" />
  </a>
</div>

<img src="https://github.com/user-attachments/assets/18fa3cac-33b9-4653-ad78-47400e2ac672" width="700" alt="Ask Shelf Screenshot">

</div>

<div align="center">

## Why I made this

A while ago my brother mentioned semantic caching in passing, and I couldn't stop thinking about it. Not the usual cache where changing a few words gives you a cache miss, but one that understands when two differently phrased questions are really asking the same thing.

I wanted to build it instead of just reading about it.

At the same time I had years of Letterboxd data sitting around, reviews, ratings, diary entries, and a watchlist. It felt like a waste to let all of that just exist as a CSV, so I decided to turn it into something I could actually have conversations with.



## What it does

</div>

- Ask questions about your watch history in plain English
- Answers are based on your own reviews, ratings, diary entries, and watchlist instead of making things up
- Uses semantic caching, so similar questions reuse previous answers even if they're worded differently
- Only calls the LLM when there's nothing relevant in the cache
- Includes a small insights terminal that shows whether the response came from the cache, your data, or a live model call, plus how many live calls have been made this session
- Saves previous questions in a history sidebar so you can revisit them anytime

## The idea

I didn't want this to feel like searching a database.

I wanted it to feel more like talking to someone who's spent hours reading your movie journal and actually remembers it. That's why the interface leans into the ticket-stub design, the little terminal, and the orange highlight whenever a live model call happens. They're small details, but they make it feel more conversational than transactional.

## Stack

- Flask
- CSV exports from Letterboxd as the knowledge base
- Semantic caching for repeated questions
- Groq for generation when a cached answer isn't available

