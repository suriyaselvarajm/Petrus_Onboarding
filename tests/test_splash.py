import pytest
from unittest.mock import patch, MagicMock
from gui.splash import SplashScreen

@patch('gui.splash.DependencyCheck')
@patch('gui.splash.check_az_logged_in')
def test_splash_screen_success(mock_az_login, mock_dep_check):
    mock_az_login.return_value = True
    
    mock_checker = MagicMock()
    mock_checker.run.return_value = (True, [], [])
    mock_dep_check.return_value = mock_checker
    
    root = MagicMock()
    splash = SplashScreen(root)
    
    with patch('threading.Thread') as mock_thread:
        # Mock thread start to just call the target function
        mock_thread.return_value.start.side_effect = lambda: mock_thread.call_args[1]['target']()
        splash._start_check()
    
    # Drain the queue
    splash._poll()
    
    assert splash.success is True
    assert splash._done is True
