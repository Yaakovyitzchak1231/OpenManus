## 2026-01-30 - Unused Cache Implementation
**Learning:** Found fully implemented but unused caching methods (`_cache_get`, `_cache_set`) in `LLM` class. Code was "dead" despite `enable_response_cache=True`.
**Action:** Always verify that "enabled" features are actually hooked up in the execution path. Search for usages of methods starting with `_` to ensure they are called.
