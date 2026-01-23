## 2026-01-23 - Unused Caching Infrastructure
**Learning:** The `LLM` class had caching configuration and helper methods implemented but not connected to the `ask` methods. This resulted in redundant API calls and wasted tokens during development/testing.
**Action:** When auditing performance, look for "dead" optimization code that exists but isn't called.
