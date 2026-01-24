## 2025-10-26 - Embedded Frontend Verification
**Learning:** The frontend is embedded as a Python string in `web_ui.py`, making it tightly coupled to the backend. Verifying UI logic requires extracting the HTML string and testing it in isolation or mocking the backend entirely, as full dependency installation is heavy.
**Action:** Use regex-based extraction scripts to generate temporary HTML files for Playwright verification, mocking `fetch` calls to simulate backend responses.
