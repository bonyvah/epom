from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    repeat_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def password_match(self):
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
