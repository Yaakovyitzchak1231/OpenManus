## 2026-10-18 - Embedded UI Constraints
**Learning:** The web interface in `web_ui.py` is embedded as a Python string literal. This enforces a specific coding style where double quotes must be escaped (`\"`) to match the existing convention, even inside triple-quoted strings. This affects how HTML attributes and JS selectors are written.
**Action:** When modifying `web_ui.py`, always verify that new double quotes are escaped as `\"` to maintain consistency with the legacy codebase style.

## 2026-10-18 - Vanilla JS State Management
**Learning:** The frontend uses vanilla JavaScript without a framework. Managing async state (loading/disabled) requires manual DOM manipulation. A robust pattern is wrapping the `fetch` call in a `try...finally` block to ensure UI controls are re-enabled even if the request fails or errors occur.
**Action:** Use `try...finally` for all async button handlers in this app to prevent "stuck" loading states.
