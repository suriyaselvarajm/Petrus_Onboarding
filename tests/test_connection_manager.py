import pytest
from unittest.mock import MagicMock
from core.connection_manager import ConnectionManager, ConnectionStatus

def test_check_all():
    mock_o365 = MagicMock()
    mock_o365.test_connection.return_value = (True, "O365 OK")
    mock_o365.get_tenant_info.return_value = {"displayName": "My Tenant"}
    
    mock_ad = MagicMock()
    mock_ad.test_connection.return_value = (True, "AD OK")
    mock_ad.check_ad_sync.return_value = (True, "Running")
    
    cm = ConnectionManager(mock_o365, mock_ad)
    
    # Callback capture
    cb_calls = []
    cm.add_callback(lambda status: cb_calls.append(status))
    
    status = cm.check_all()
    
    assert status.o365_connected is True
    assert status.o365_message == "O365 OK"
    assert status.o365_tenant == "My Tenant"
    
    assert status.ad_connected is True
    assert status.ad_message == "AD OK"
    
    assert status.ad_sync_running is True
    assert status.ad_sync_message == "Running"
    
    assert len(cb_calls) == 1
    assert cb_calls[0] == status
