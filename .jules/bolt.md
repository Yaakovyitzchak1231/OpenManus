## 2026-01-25 - [LLM Input Mutation & Caching]
**Learning:** `LLM.format_messages` and `ask_with_images` were mutating input dictionaries in place (appending images to content). This caused cache misses for identical subsequent requests because the input `messages` structure was permanently altered.
**Action:** Always ensure utility functions like `format_messages` create copies (shallow or deep as needed) of mutable input structures before modification. Specifically, added `message = message.copy()` in `format_messages` and explicit list copying in `ask_with_images`.
