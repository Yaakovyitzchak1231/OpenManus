# Palette's Journal

## 2025-03-07 - Embedded Frontend Verification
**Learning:** The application uses a single-file embedded frontend architecture (`web_ui.py`) where HTML/JS is stored as an escaped Python string. This makes standard frontend testing tools incompatible out-of-the-box.
**Action:** When verifying UX changes, verify by extracting the HTML string, unescaping it (replacing `\"` with `"`), and running Playwright against the local file with `window.fetch` mocked.
