import re
import os

def test_web_ui_ux_improvements():
    """
    Verifies that the UX improvements are present in web_ui.py.
    """
    filepath = "web_ui.py"
    if not os.path.exists(filepath):
        # Fallback if running from tests/ directory
        filepath = "../web_ui.py"

    with open(filepath, "r") as f:
        content = f.read()

    # 1. Check for Aria Label on textarea
    # Looking for: aria-label=\"Message to Manus\"
    # The quotes might be escaped in the string literal
    assert 'aria-label=\\"Message to Manus\\"' in content, "Missing aria-label on textarea"

    # 2. Check for Role Log / Aria Live on messages container
    # Looking for: role=\"log\" aria-live=\"polite\"
    assert 'role=\\"log\\"' in content, "Missing role='log' on messages container"
    assert 'aria-live=\\"polite\\"' in content, "Missing aria-live='polite' on messages container"

    # 3. Check for Disabled Button CSS
    # Looking for: button:disabled {
    assert 'button:disabled {' in content, "Missing CSS for disabled button"
    assert 'opacity: 0.7;' in content, "Missing opacity style for disabled button"
    assert 'cursor: not-allowed;' in content, "Missing cursor style for disabled button"

    # 4. Check for Ctrl+Enter logic
    # Looking for: if ((e.ctrlKey || e.metaKey) && e.key === 'Enter')
    assert 'e.ctrlKey' in content, "Missing Ctrl key check"
    assert 'e.metaKey' in content, "Missing Meta key check"
    assert "e.key === 'Enter'" in content, "Missing Enter key check"

    # 5. Check for Thinking state
    # Looking for: submitBtn.textContent = 'Thinking...';
    assert "submitBtn.textContent = 'Thinking...';" in content, "Missing Thinking... state text"

    print("All UX improvements verified successfully!")

if __name__ == "__main__":
    test_web_ui_ux_improvements()
