# Palette's Journal

## 2024-05-22 - Verifying Embedded HTML Apps
**Learning:** Verifying frontend interactions in a single-file Python app (FastAPI + embedded HTML) requires extracting the HTML string and serving it via a local HTTP server. The `file://` protocol blocks the `fetch` API calls used in the app, preventing testing of network-dependent states like "Thinking..." or disabled buttons.
**Action:** For similar architectures, verify by extracting the HTML string to a temporary `index.html` and running a transient local server (e.g., `python -m http.server`) for Playwright to interact with.
