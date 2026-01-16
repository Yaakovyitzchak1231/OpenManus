## 2026-01-16 - Frontend Performance in Python Web UI
**Learning:** The `web_ui.py` serves raw HTML strings with blocking `@import` for fonts, which significantly delays First Contentful Paint.
**Action:** When optimizing single-file Python web UIs, always check for blocking resources in the embedded HTML string, as standard frontend build tools are absent.

## 2026-01-16 - Environment Dependency Constraints
**Learning:** The sandbox environment may lack project dependencies (`fastapi`, etc.) by default, and installing them can be slow or flaky.
**Action:** Use `unittest.mock` to verify logic in isolation (like HTML string generation) without requiring the full application stack to be installed.
