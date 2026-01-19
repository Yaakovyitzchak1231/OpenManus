## 2026-01-19 - [LLM Caching Enabled]
**Learning:** `LLM.ask` and `ask_with_images` had caching infrastructure but it was completely unused, causing every repeated request to hit the API.
**Action:** Implemented caching logic in `ask` and `ask_with_images` while preserving `stream=True` side effects (printing to stdout) by printing cached content.
