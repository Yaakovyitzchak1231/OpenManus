import re

with open('web_ui.py', 'r') as f:
    content = f.read()

match = re.search(r'def _html_page\(\) -> str:\n\s+return """(.*?)"""', content, re.DOTALL)
if match:
    html = match.group(1)
    with open('temp_ui.html', 'w') as f:
        f.write(html)
    print("Extracted HTML to temp_ui.html")
else:
    print("Could not find HTML string")
