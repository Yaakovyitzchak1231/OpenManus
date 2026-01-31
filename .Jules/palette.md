## 2026-01-31 - Chat Interaction Standards
**Learning:** Users expect "Enter" to submit and "Shift+Enter" for newlines in chat interfaces. The default `<textarea>` behavior (Enter = newline) feels broken in this context.
**Action:** Always implement a `keydown` listener on chat inputs to handle Enter/Shift+Enter behavior, and ensure `localStorage` access is wrapped in try/catch to prevent crashes in restricted environments (like embedded views or test runners).
