from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.db.base import SessionLocal
from apps.api.db.models import PlatformAccount
from apps.api.schemas.accounts import AccountCreateRequest, AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def _validate_credential_ref(value: str | None) -> str | None:
    if not value:
        return None
    root = settings.secret_root.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise HTTPException(status_code=400, detail="credential_ref must point inside SECRET_ROOT")
    return str(resolved)


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(request: AccountCreateRequest) -> AccountResponse:
    credential_ref = _validate_credential_ref(request.credential_ref)
    with SessionLocal() as session:
        row = PlatformAccount(platform=request.platform, account_name=request.account_name.strip(), credential_ref=credential_ref, enabled=True)
        session.add(row)
        session.commit()
        session.refresh(row)
        return AccountResponse(id=row.id, platform=row.platform, account_name=row.account_name, enabled=row.enabled)


@router.get("", response_model=list[AccountResponse])
def list_accounts() -> list[AccountResponse]:
    with SessionLocal() as session:
        rows = session.scalars(select(PlatformAccount).order_by(PlatformAccount.platform, PlatformAccount.id)).all()
        return [AccountResponse(id=row.id, platform=row.platform, account_name=row.account_name, enabled=row.enabled) for row in rows]


@router.post("/{account_id}/disable", response_model=AccountResponse)
def disable_account(account_id: int) -> AccountResponse:
    with SessionLocal() as session:
        row = session.get(PlatformAccount, account_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")
        row.enabled = False
        session.commit()
        return AccountResponse(id=row.id, platform=row.platform, account_name=row.account_name, enabled=row.enabled)
