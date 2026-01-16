import sys
from unittest.mock import MagicMock


# Create mocks for dependencies
mock_fastapi = MagicMock()
mock_fastapi.FastAPI = MagicMock
mock_fastapi.HTTPException = Exception
mock_fastapi.responses = MagicMock()
mock_fastapi.responses.HTMLResponse = MagicMock

mock_pydantic = MagicMock()


class MockBaseModel:
    pass


mock_pydantic.BaseModel = MockBaseModel

# Mock app.config
mock_app_config = MagicMock()
mock_app_config.config = MagicMock()
mock_app_config.config.root_path = MagicMock()
# Setup Path behavior
mock_path = MagicMock()
mock_path.__truediv__.return_value = mock_path  # support / operator
mock_app_config.config.root_path = mock_path

# Mock app.harness.recording
mock_app_harness_recording = MagicMock()

# Install mocks into sys.modules
sys.modules["fastapi"] = mock_fastapi
sys.modules["fastapi.responses"] = mock_fastapi.responses
sys.modules["pydantic"] = mock_pydantic
sys.modules["app"] = MagicMock()
sys.modules["app.config"] = mock_app_config
sys.modules["app.harness"] = MagicMock()
sys.modules["app.harness.recording"] = mock_app_harness_recording

# Now we can import web_ui
sys.path.append(".")
import web_ui


def test_font_loading_optimization():
    html = web_ui._html_page()

    # Check for presence of optimized link tags
    has_preconnect_googleapis = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">' in html
    )
    has_preconnect_gstatic = (
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' in html
    )
    has_stylesheet = (
        'href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=Libre+Baskerville:ital@0;1&display=swap" rel="stylesheet"'
        in html
    )

    # Check for absence of blocking import
    has_import = "@import url" in html

    errors = []
    if not has_preconnect_googleapis:
        errors.append("Missing preconnect to googleapis")
    if not has_preconnect_gstatic:
        errors.append("Missing preconnect to gstatic")
    if not has_stylesheet:
        errors.append("Missing stylesheet link")
    if has_import:
        errors.append("Blocking @import found (should be removed)")

    if errors:
        raise AssertionError("\n".join(errors))


if __name__ == "__main__":
    try:
        test_font_loading_optimization()
        print("✅ Font loading optimization verification passed!")
    except AssertionError as e:
        print(f"❌ Verification failed:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
