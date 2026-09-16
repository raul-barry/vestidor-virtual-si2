from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: str | None


class CreateCategoryRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None
    estado: str | None = "ACTIVO"


class UpdateCategoryRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = None
    estado: str | None = None


class CategoryAdminResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: str | None
    estado: str
