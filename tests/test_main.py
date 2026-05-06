import pytest
from unittest.mock import patch, MagicMock
from main import main

@patch('main.tk.Tk')
@patch('gui.splash.SplashScreen')
@patch('gui.app.OnboardingApp')
def test_main_success(mock_app, mock_splash, mock_tk):
    mock_root = MagicMock()
    mock_tk.return_value = mock_root
    
    # Setup splash success
    splash_instance = mock_splash.return_value
    splash_instance.success = True
    
    main()
    
    mock_root.withdraw.assert_called_once()
    mock_root.wait_window.assert_called_once_with(splash_instance)
    mock_root.deiconify.assert_called_once()
    mock_app.assert_called_once_with(mock_root)
    mock_root.mainloop.assert_called_once()

@patch('main.tk.Tk')
@patch('gui.splash.SplashScreen')
@patch('main.sys.exit')
def test_main_failure(mock_exit, mock_splash, mock_tk):
    mock_root = MagicMock()
    mock_tk.return_value = mock_root
    
    # Setup splash failure
    splash_instance = mock_splash.return_value
    splash_instance.success = False
    mock_exit.side_effect = SystemExit
    
    with pytest.raises(SystemExit):
        main()
    
    mock_root.destroy.assert_called_once()
    mock_exit.assert_called_once_with(0)
