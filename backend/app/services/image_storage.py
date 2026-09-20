from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


class LocalImageStorage:
    allowed = {
        "image/jpeg": {"suffix": ".jpg", "extensions": {".jpg", ".jpeg"}},
        "image/png": {"suffix": ".png", "extensions": {".png"}},
        "image/webp": {"suffix": ".webp", "extensions": {".webp"}},
    }
    max_bytes = 5 * 1024 * 1024

    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[1] / "assets" / "uploads"
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> str:
        config = self.allowed.get(file.content_type or "")
        extension = Path(file.filename or "").suffix.lower()
        if not config or extension not in config["extensions"]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Formato no permitido. Usa JPG, PNG o WebP",
            )
        content = await file.read(self.max_bytes + 1)
        if len(content) > self.max_bytes:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La imagen supera 5 MB")
        if not content or not self._signature_matches(file.content_type or "", content):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El contenido no corresponde a una imagen válida")

        name = f"{uuid4().hex}{config['suffix']}"
        (self.root / name).write_bytes(content)
        return f"/api/assets/uploads/{name}"

    def delete(self, url: str | None) -> None:
        if not url or not url.startswith("/api/assets/uploads/"):
            return
        path = (self.root / Path(url).name).resolve()
        if path.parent == self.root.resolve() and path.exists():
            path.unlink()

    @staticmethod
    def _signature_matches(content_type: str, content: bytes) -> bool:
        if content_type == "image/jpeg":
            return content.startswith(b"\xff\xd8\xff")
        if content_type == "image/png":
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if content_type == "image/webp":
            return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
        return False
