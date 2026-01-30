## 2025-05-15 - Embedded UI Testing
**Learning:** Testing the embedded frontend in `web_ui.py` requires extracting the HTML string. Playwright's `press('Enter')` on a `textarea` can trigger unexpected implicit submission behavior in headless environments, requiring careful verification of event counts.
**Action:** When testing embedded UIs, always assert against state changes (e.g. input cleared) rather than just event call counts, or handle potential double-fire events gracefully.
