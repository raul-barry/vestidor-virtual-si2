from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    correo: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class AuthenticatedUserResponse(BaseModel):
    id_usuario: int
    correo: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: AuthenticatedUserResponse
    rol: str


class LogoutResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    correo: str = Field(min_length=1, max_length=255)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    nueva_password: str = Field(min_length=8)


class PasswordResetTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=255)


class PasswordResetResponse(BaseModel):
    message: str
    token: str | None = None


class RegisterRequest(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=1, max_length=255)
    telefono: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    telefono: str | None
    rol: str
