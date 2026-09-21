from pydantic import BaseModel, Field


class BranchResponse(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str
    estado: str


class CreateBranchRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    direccion: str = Field(min_length=1, max_length=255)
    ciudad: str | None = "Santa Cruz"


class UpdateBranchRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    direccion: str | None = Field(default=None, min_length=1, max_length=255)
    ciudad: str | None = None


class BranchAdminResponse(BaseModel):
    id_sucursal: int
    nombre: str
    direccion: str
    ciudad: str | None = None
    estado: str

