import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.user_form import UserForm

@pytest.fixture
def mock_root():
    m = MagicMock()
    return m

@pytest.fixture
def mock_o365():
    m = MagicMock()
    m.get_skus.return_value = [{"id": "s1", "skuPartNumber": "ENTERPRISEPACK"}]
    m.get_groups.return_value = [{"id": "g1", "displayName": "Group 1", "_type": "M365 Group"}]
    return m

@pytest.fixture
def mock_ad():
    m = MagicMock()
    m.get_ous.return_value = [{"Name": "OU1", "DistinguishedName": "OU=OU1,DC=local"}]
    m.get_groups.return_value = [{"Name": "ADGroup1", "DistinguishedName": "CN=G1,OU=OU1"}]
    # Ensure AD methods return expected tuples for unpacking
    m.create_user.return_value = (True, "sam_account_name")
    m.set_proxy_addresses.return_value = (True, "OK")
    m.add_to_group.return_value = (True, "OK")
    m.get_manager_dn.return_value = "CN=Manager,DC=local"
    return m

def setup_form_mocks(form):
    """Helper to set default return values for widget/variable mocks."""
    # List of all StringVar attributes to initialize
    vars = ["v_first", "v_last", "v_email", "v_pwd", "v_mobile", "v_emp_type", 
            "v_city", "v_state", "v_zip", "v_country", "v_street", "v_office",
            "v_o365_alias", "v_license", "v_emp_id", "v_job_title", "v_dept",
            "v_primary_smtp", "v_alias", "v_mfa"]
    
    for attr in vars:
        if hasattr(form, attr):
            var = getattr(form, attr)
            var.get.return_value = ""
    
    # Mock Comboboxes and other widgets
    widgets = ["_sub_ou_cb", "_ou_cb", "_mgr_combo", "_license_hint", "_email_hint"]
    for attr in widgets:
        if hasattr(form, attr):
            w = getattr(form, attr)
            if hasattr(w, "current"):
                w.current.return_value = -1
            if hasattr(w, "winfo_ismapped"):
                w.winfo_ismapped.return_value = False
    
    if hasattr(form, "v_force_pwd"):
        form.v_force_pwd.get.return_value = True

def test_user_form_initialization(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    assert form is not None

def test_user_form_collect(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    form.v_last.get.return_value = "Doe"
    form.v_email.get.return_value = "jdoe@example.com"
    form.v_emp_type.get.return_value = "Permanent"
    form.v_license.get.return_value = "Microsoft 365 Business Basic"
    
    data = form._collect()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "jdoe@example.com"

def test_user_form_validation(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    form.v_last.get.return_value = "Doe"
    form.v_email.get.return_value = "jdoe@example.com"
    form.v_pwd.get.return_value = "Password123!"
    form.v_mobile.get.return_value = "1234567890"
    
    ok, _ = form._validate()
    assert ok is True

def test_on_submit_creation_flow_success(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    form.v_last.get.return_value = "Doe"
    form.v_email.get.return_value = "jdoe@example.com"
    form.v_pwd.get.return_value = "Pass123!"
    form.v_mobile.get.return_value = "1234567890"
    
    mock_o365.email_exists.return_value = False
    
    with patch('threading.Thread') as mock_thread, \
         patch('tkinter.messagebox.askyesno') as mock_ask:
        
        mock_ask.return_value = True
        
        def side_effect(target=None, args=(), **kwargs):
            target(*args)
            return MagicMock()
        mock_thread.side_effect = side_effect
        
        mock_o365.create_user.return_value = (True, "o365_id", "")
        mock_o365.wait_for_user_provisioned.return_value = (True, "")
        mock_o365.set_mail_address.return_value = (True, "")
        mock_o365.assign_license.return_value = (True, "")
        mock_o365.wait_for_mailbox.return_value = (True, "")
        mock_o365.add_o365_alias.return_value = (True, "")
        mock_o365.add_to_group.return_value = (True, "")
        mock_o365.add_to_zoho_enterprise_app.return_value = (True, "")
        mock_o365.enable_mfa.return_value = (True, "MFA Enabled")
        
        form._on_submit()
        assert mock_ad.create_user.called
        assert mock_o365.create_user.called

def test_on_submit_creation_flow_o365_fail(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    form.v_last.get.return_value = "Doe"
    form.v_email.get.return_value = "jdoe@example.com"
    form.v_pwd.get.return_value = "Pass123!"
    form.v_mobile.get.return_value = "1234567890"
    
    mock_o365.email_exists.return_value = False
    mock_o365.create_user.return_value = (False, "", "Quota exceeded")
    
    with patch('threading.Thread') as mock_thread, \
         patch('tkinter.messagebox.askyesno') as mock_ask:
        mock_ask.return_value = True
        def side_effect(target=None, args=(), **kwargs):
            target(*args)
            return MagicMock()
        mock_thread.side_effect = side_effect
        
        form._on_submit()
        assert not mock_ad.create_user.called

def test_on_submit_creation_flow_retry_logic(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    form.v_last.get.return_value = "Doe"
    form.v_email.get.return_value = "jdoe@example.com"
    form.v_pwd.get.return_value = "Pass123!"
    form.v_mobile.get.return_value = "1234567890"
    form.v_o365_alias.get.return_value = "jdoe_alias@example.com"
    
    mock_o365.email_exists.return_value = False
    
    with patch('threading.Thread') as mock_thread, \
         patch('tkinter.messagebox.askyesno') as mock_ask:
        mock_ask.return_value = True
        def side_effect(target=None, args=(), **kwargs):
            target(*args)
            return MagicMock()
        mock_thread.side_effect = side_effect
        
        mock_o365.create_user.return_value = (True, "o365_id", "")
        mock_o365.wait_for_user_provisioned.return_value = (True, "")
        mock_o365.set_mail_address.return_value = (True, "")
        mock_o365.assign_license.return_value = (True, "")
        mock_o365.wait_for_mailbox.return_value = (False, "Timeout")
        mock_o365.add_o365_alias.return_value = (False, "Error")
        mock_o365.add_to_group.return_value = (True, "OK")
        mock_o365.add_to_zoho_enterprise_app.return_value = (True, "OK")
        mock_o365.enable_mfa.return_value = (True, "MFA Enabled")
        
        form._on_submit()
        assert mock_o365.add_o365_alias.called

def test_clear_form(mock_root, mock_o365, mock_ad):
    form = UserForm(mock_root, mock_o365, mock_ad)
    setup_form_mocks(form)
    
    form.v_first.get.return_value = "John"
    with patch('tkinter.messagebox.askyesno') as mock_ask:
        mock_ask.return_value = True
        form._clear_form()
    form.v_first.set.assert_called_with("")
