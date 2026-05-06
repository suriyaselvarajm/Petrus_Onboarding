import pytest
from unittest.mock import MagicMock, patch
from gui.app import OnboardingApp

def test_app_initialization():
    with patch('gui.app.apply_theme'), \
         patch('gui.app.ConnectionManager'):
        
        root = MagicMock()
        app = OnboardingApp(root)
        assert app is not None

def test_app_status_update():
    with patch('gui.app.apply_theme'), \
         patch('gui.app.ConnectionManager'), \
         patch('gui.app.UserForm') as mock_form:
        
        root = MagicMock()
        app = OnboardingApp(root)
        
        status = MagicMock()
        status.ready = True
        status.o365_ok = True
        status.ad_ok = True
        app._apply_status(status)
        assert mock_form.called
