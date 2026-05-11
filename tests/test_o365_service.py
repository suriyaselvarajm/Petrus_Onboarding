import pytest
from unittest.mock import patch, MagicMock
from core.o365_service import O365Service

@pytest.fixture
def o365():
    with patch('core.o365_service._fetch_az_token') as mock_token:
        mock_token.return_value = "fake_token"
        service = O365Service()
        return service

def test_get_users(o365):
    with patch.object(o365, '_get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "value": [{"id": "1", "displayName": "User 1", "userPrincipalName": "u1@example.com"}]
        }
        users = o365.get_users(search="test")
        assert len(users) == 1
        assert users[0]["displayName"] == "User 1"

def test_get_groups(o365):
    with patch.object(o365, '_get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "id": "g1", "displayName": "Group 1", "groupTypes": ["Unified"],
                    "mailEnabled": True, "securityEnabled": False
                },
                {
                    "id": "g2", "displayName": "Group 2", "groupTypes": [],
                    "mailEnabled": True, "securityEnabled": False
                }
            ]
        }
        groups = o365.get_groups()
        assert len(groups) == 2
        assert groups[0]["_type"] == "M365 Group"
        assert groups[1]["_type"] == "Distribution List"

def test_get_distribution_lists(o365):
    with patch.object(o365, '_get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"value": [{"id": "dl1"}]}
        dls = o365.get_distribution_lists()
        assert len(dls) == 1

def test_create_user_success(o365):
    with patch.object(o365, '_post') as mock_post:
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": "new_id"}
        
        data = {
            "first_name": "Test", "last_name": "User", "email": "test@example.com",
            "password": "password", "mail_nickname": "testuser", "hire_date_iso": "2023-01-01T00:00:00Z"
        }
        ok, uid, _ = o365.create_user(data)
        assert ok is True
        assert uid == "new_id"

def test_assign_license_success(o365):
    with patch.object(o365, '_post') as mock_post:
        with patch.object(o365, '_ensure_usage_location'):
            mock_post.return_value.status_code = 200
            ok, msg = o365.assign_license("user_id", "sku_id")
            assert ok is True
            assert "License assigned" in msg

def test_add_to_group(o365):
    with patch.object(o365, '_post') as mock_post:
        mock_post.return_value.status_code = 204
        ok, _ = o365.add_to_group("user_id", "group_id")
        assert ok is True

def test_set_manager(o365):
    with patch.object(o365, '_put') as mock_put:
        mock_put.return_value.status_code = 204
        ok, _ = o365.set_manager("user_id", "mgr_id")
        assert ok is True

def test_add_o365_alias_success(o365):
    with patch.object(o365, '_get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"proxyAddresses": []}
        with patch.object(o365, '_patch') as mock_patch:
            mock_patch.return_value.status_code = 204
            ok, _ = o365.add_o365_alias("user_id", "alias@example.com")
            assert ok is True

def test_email_exists(o365):
    with patch.object(o365, '_get') as mock_get:
        m1 = MagicMock(); m1.status_code = 200
        m2 = MagicMock(); m2.status_code = 404
        mock_get.side_effect = [m1, m2]
        assert o365.email_exists("test@example.com") is True
        assert o365.email_exists("notfound@example.com") is False

def test_wait_for_replication(o365):
    with patch.object(o365, '_get') as mock_get:
        m1 = MagicMock(); m1.status_code = 404
        m2 = MagicMock(); m2.status_code = 200
        mock_get.side_effect = [m1, m2]
        with patch('time.sleep'):
            ok, _ = o365.wait_for_replication("user_id", max_wait=10)
            assert ok is True

def test_wait_for_mailbox(o365):
    with patch.object(o365, '_get') as mock_get:
        m1 = MagicMock(); m1.status_code = 404
        m2 = MagicMock(); m2.status_code = 200
        mock_get.side_effect = [m1, m2]
        with patch('time.sleep'):
            ok, _ = o365.wait_for_mailbox("user_id", max_wait=20)
            assert ok is True

def test_find_service_principal(o365):
    with patch.object(o365, '_get') as mock_get:
        # Mocking the broad search logic
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"value": [{"id": "sp_id", "displayName": "App Name"}]}
        sp = o365._find_service_principal("App Name")
        assert sp["id"] == "sp_id"
