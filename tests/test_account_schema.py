import pytest
from pydantic import ValidationError

from apps.api.schemas.accounts import AccountCreateRequest


def test_account_name_is_trimmed():
    request = AccountCreateRequest(platform="youtube", account_name="  My Channel  ")
    assert request.account_name == "My Channel"


def test_account_name_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="account_name must not be blank"):
        AccountCreateRequest(platform="youtube", account_name="   ")
