# Palette's Journal

## 2026-01-24 - Initial Discovery
**Learning:** The frontend is embedded directly in a Python string in `web_ui.py`. This means any UX changes must be careful with string escaping and don't have a build step like Webpack/Vite.
**Action:** When making changes, ensure to verify the resulting HTML string is valid and that no syntax errors are introduced in the Python file.
