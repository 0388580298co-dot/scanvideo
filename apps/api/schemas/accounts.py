from pydantic import BaseModel, Field, field_validator


class AccountCreateRequest(BaseModel):
    platform: str = Field(pattern=r"^(youtube|tiktok)$")
    account_name: str = Field(min_length=1, max_length=160)
    credential_ref: str | None = Field(default=None, max_length=255)

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("account_name must not be blank")
        return value


class AccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    enabled: bool
