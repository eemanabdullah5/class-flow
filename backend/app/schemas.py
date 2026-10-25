from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import MAX_PASSWORD_BYTES

# Pydantic models describe the exact shape of data coming in and going out.
# FastAPI checks every request against them and replies 422 if the data is invalid.


class RegisterRequest(BaseModel):
    # "forbid" rejects unknown fields, so sending {"role": "teacher"} fails with 422.
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        return email.lower()

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, full_name: str) -> str:
        full_name = full_name.strip()
        if not full_name:
            raise ValueError("Full name cannot be blank.")
        return full_name

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        # Some characters (e.g. emoji) use several bytes, so check bytes, not just length.
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        return email.lower()


class UserOut(BaseModel):
    """What the API shows about a user. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)  # can be built from a User model object

    id: int
    email: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
