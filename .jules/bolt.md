## 2026-01-26 - [LLM Input Mutation causing Cache Misses]
**Learning:** `LLM.format_messages` was modifying input dictionaries in-place (appending references), causing subsequent calls with the same input variable to send mutated messages (e.g. duplicated images), leading to cache misses.
**Action:** Always strictly copy mutable inputs (dicts/lists) in utility functions that prepare data for APIs, especially when those inputs might be reused in a loop or across retries.

## 2026-01-26 - [Unimplemented Caching Infrastructure]
**Learning:** The `LLM` class had a complete LRU cache infrastructure (`_cache_get`, `_cache_set`, `_response_cache`) defined but completely unused in the main execution methods (`ask`, `ask_with_images`).
**Action:** Before writing new caching logic, always check if the class already has unused/dormant caching capabilities that just need to be wired up.
