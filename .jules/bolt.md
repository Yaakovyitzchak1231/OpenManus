## 2026-01-31 - LLM Caching Implementation
**Learning:** `LLM.ask` is designed for text-only interactions and does not support tools, making it safe to cache based on messages and model parameters. `ask_tool` handles tools and should not be cached (or requires careful caching) to avoid side effects.
**Action:** When optimizing agentic loops, distinguish between pure generation steps (cachable) and tool execution steps (non-cachable).

**Learning:** `LLM` class relies on stdout printing for streaming feedback. Caching must replicate this side effect to maintain user experience.
**Action:** Ensure cached responses replay side effects like printing if the caller expects them (e.g. `stream=True`).
