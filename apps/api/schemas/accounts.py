from pydantic import BaseModel, Field


class AccountCreateRequest(BaseModel):
    platform: str = Field(pattern=r"^(youtube|tiktok)$")
    account_name: str = Field(min_length=1, max_length=160)
    credential_ref: str | None = Field(default=None, max_length=255)


class AccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    enabled: bool
