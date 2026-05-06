import pytest
import subprocess
import json
from unittest.mock import patch, MagicMock
from core.ad_service import ADService

@pytest.fixture
def ad():
    return ADService()

def test_get_ous(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"Name": "OU1", "DistinguishedName": "OU=OU1,DC=local"}]'
        mock_run.return_value.stderr = ''
        ous = ad.get_ous()
        assert len(ous) == 1
        assert ous[0]["Name"] == "OU1"

def test_get_groups_under_ou(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"Name": "Group1", "DistinguishedName": "CN=G1,OU=OU1"}]'
        mock_run.return_value.stderr = ''
        groups = ad.get_groups(search_base="OU=OU1,DC=local")
        assert len(groups) == 1
        assert groups[0]["Name"] == "Group1"

def test_create_user_success(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'SUCCESS:test.user'
        mock_run.return_value.stderr = ''
        
        data = {
            "first_name": "Test", "last_name": "User", "display_name": "Test User",
            "email": "test@example.com", "password": "Password123!",
            "ad_ou_dn": "OU=Users,DC=local", "sam_account_name": "test.user",
            "user_principal_name": "test@example.com"
        }
        ok, sam = ad.create_user(data)
        assert ok is True
        assert sam == "test.user"

def test_get_manager_dn(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'CN=Manager,OU=Users,DC=local'
        mock_run.return_value.stderr = ''
        dn = ad.get_manager_dn("manager@example.com")
        assert dn == "CN=Manager,OU=Users,DC=local"

def test_get_manager_dn_not_found(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ''
        mock_run.return_value.stderr = ''
        dn = ad.get_manager_dn("notfound@example.com")
        assert dn is None

def test_set_proxy_addresses(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'SUCCESS'
        mock_run.return_value.stderr = ''
        ok, msg = ad.set_proxy_addresses("testuser", "test@example.com", "EMP123")
        assert ok is True
        assert "SUCCESS" in msg

def test_add_to_group(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'SUCCESS'
        mock_run.return_value.stderr = ''
        ok, _ = ad.add_to_group("testuser", "CN=Group,DC=local")
        assert ok is True

def test_test_connection_success(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'OK:petrus.local'
        mock_run.return_value.stderr = ''
        ok, msg = ad.test_connection()
        assert ok is True
        assert msg == "petrus.local"
        assert ad._connected is True

def test_check_ad_sync(ad):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'Running'
        mock_run.return_value.stderr = ''
        running, status = ad.check_ad_sync()
        assert running is True
        assert "Running" in status
