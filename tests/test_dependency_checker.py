import pytest
from unittest.mock import patch, MagicMock
from core.dependency_checker import DependencyCheck, check_python_package, check_azure_cli, check_az_logged_in, check_ps_ad_module

@patch('core.dependency_checker.importlib.import_module')
def test_check_python_package(mock_import):
    assert check_python_package("requests") is True
    mock_import.side_effect = ImportError
    assert check_python_package("missing_pkg") is False

@patch('core.dependency_checker.shutil.which')
def test_check_azure_cli(mock_which):
    mock_which.return_value = "/usr/bin/az"
    assert check_azure_cli() is True
    mock_which.return_value = None
    assert check_azure_cli() is False

@patch('core.dependency_checker._run')
def test_check_az_logged_in(mock_run):
    mock_run.return_value = (True, '{"id": "some-id"}', "")
    assert check_az_logged_in() is True
    
    mock_run.return_value = (False, '', "Not logged in")
    assert check_az_logged_in() is False

@patch('core.dependency_checker._run')
def test_check_ps_ad_module(mock_run):
    mock_run.return_value = (True, "", "")
    assert check_ps_ad_module() is True

@patch('core.dependency_checker.check_python_package')
@patch('core.dependency_checker.check_azure_cli')
@patch('core.dependency_checker.check_ps_ad_module')
@patch('core.dependency_checker.check_az_logged_in')
def test_dependency_check_run_all_ok(mock_az_login, mock_ad_mod, mock_az_cli, mock_py_pkg):
    mock_py_pkg.return_value = True
    mock_az_cli.return_value = True
    mock_ad_mod.return_value = True
    mock_az_login.return_value = True
    
    checker = DependencyCheck()
    all_ok, issues, warnings = checker.run()
    
    assert all_ok is True
    assert len(issues) == 0
    assert len(warnings) == 0

@patch('core.dependency_checker.check_python_package')
@patch('core.dependency_checker.check_azure_cli')
@patch('core.dependency_checker.check_ps_ad_module')
@patch('core.dependency_checker.check_az_logged_in')
@patch('core.dependency_checker.install_python_package')
@patch('core.dependency_checker.install_rsat')
def test_dependency_check_run_failures(mock_install_rsat, mock_install_pkg, mock_az_login, mock_ad_mod, mock_az_cli, mock_py_pkg):
    # Simulate missing dependencies that fail to install
    mock_py_pkg.return_value = False
    mock_install_pkg.return_value = False
    mock_az_cli.return_value = False
    mock_ad_mod.return_value = False
    mock_install_rsat.return_value = False
    mock_az_login.return_value = False
    
    checker = DependencyCheck()
    all_ok, issues, warnings = checker.run()
    
    assert all_ok is False
    assert len(issues) > 0
    assert len(warnings) > 0
