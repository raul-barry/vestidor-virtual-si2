from pydantic import BaseModel


class VirtualTryOnResponse(BaseModel):
    image_base64: str
    mime_type: str = "image/png"
    id_producto: int
    id_variante: int | None = None
    nombre: str
    talla: str | None = None
    color: str | None = None
