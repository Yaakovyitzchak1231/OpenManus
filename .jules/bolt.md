## 2026-01-22 - Mutable Inputs in LLM.format_messages
**Learning:** The `LLM.format_messages` utility modifies input message dictionaries in place (via `to_dict()` or direct usage). This mutation causes side effects in `ask_with_images` where images are appended to the *original* message list reference. This breaks caching logic because subsequent calls have different content (duplicated images).
**Action:** Always deep copy mutable inputs (dicts/lists) in utility functions before modification, especially when those inputs are used for cache key generation or reused across calls.
