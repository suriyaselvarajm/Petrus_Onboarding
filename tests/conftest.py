import sys
from unittest.mock import MagicMock, patch
from contextlib import ExitStack
import pytest

# CRITICAL: Mock these BEFORE any other imports happen during pytest collection
sys.modules["_tkinter"] = MagicMock()
sys.modules["tkcalendar"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageTk"] = MagicMock()

@pytest.fixture(autouse=True, scope="session")
def mock_gui_session():
    patches = [
        "tkinter.Tk", "tkinter.Toplevel", "tkinter.Frame", "tkinter.Canvas",
        "tkinter.Label", "tkinter.Button", "tkinter.Entry", "tkinter.Text",
        "tkinter.Menu", "tkinter.messagebox", "tkinter.filedialog", "tkinter.Checkbutton",
        "tkinter.ttk.Frame", "tkinter.ttk.Button", "tkinter.ttk.Label",
        "tkinter.ttk.Entry", "tkinter.ttk.Combobox", "tkinter.ttk.Scrollbar",
        "tkinter.ttk.Progressbar", "tkinter.ttk.Separator",
        "tkinter.PhotoImage"
    ]
    
    with ExitStack() as stack:
        for p in patches:
            try:
                stack.enter_context(patch(p, return_value=MagicMock()))
            except (ImportError, AttributeError):
                pass
        
        # These need to return a NEW mock every time they are called
        stack.enter_context(patch("tkinter.StringVar", side_effect=lambda *a, **k: MagicMock()))
        stack.enter_context(patch("tkinter.BooleanVar", side_effect=lambda *a, **k: MagicMock()))
        stack.enter_context(patch("tkinter.IntVar", side_effect=lambda *a, **k: MagicMock()))
        stack.enter_context(patch("tkinter.DoubleVar", side_effect=lambda *a, **k: MagicMock()))
        
        yield
