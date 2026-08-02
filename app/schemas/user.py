from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    login: str
    password: str = Field(min_length=8)
    repeat_password: str

    @model_validator(mode="after")
    def password_match(self):
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"