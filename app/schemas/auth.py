from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None
    backup_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class Enable2FAResponse(BaseModel):
    secret: str
    uri: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    totp_code: str


class Disable2FARequest(BaseModel):
    password: str
    totp_code: str | None = None
    backup_code: str | None = None


class ResendVerificationRequest(BaseModel):
    email: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CreateApiKeyRequest(BaseModel):
    name: str
    expires_in_days: int | None = None


class CreateApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    created_at: str
    expires_at: str | None