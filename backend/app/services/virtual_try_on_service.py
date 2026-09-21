"""Private, photo-based virtual try-on providers.

The local provider intentionally produces an *approximate visual composition*.
It does not persist customer photos or outputs: callers receive the rendered
PNG bytes and are responsible for returning them in the current response.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

try:  # Optional: the deployed dependency improves positioning, never blocks Pillow fallback.
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - exercised by environments without OpenCV.
    cv2 = None
    np = None


class VirtualTryOnProvider(ABC):
    @abstractmethod
    def render(self, person: bytes, garment_path: Path) -> bytes: ...


class LocalTryOnProvider(VirtualTryOnProvider):
    """Approximate local overlay with a face-anchored torso estimate and Pillow fallback."""

    @staticmethod
    def _default_torso(base: Image.Image) -> tuple[int, int, int, int]:
        width, height = base.size
        return (int(width * .23), int(height * .20), int(width * .54), int(height * .48))

    def _estimate_torso(self, base: Image.Image) -> tuple[int, int, int, int]:
        """Infer shoulders/torso from the largest frontal face when OpenCV is available."""
        fallback = self._default_torso(base)
        if cv2 is None or np is None:
            return fallback
        try:
            pixels = np.array(base.convert("RGB"))
            gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
            detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.12, minNeighbors=4,
                minSize=(max(24, base.width // 14), max(24, base.height // 14)),
            )
            if len(faces) == 0:
                return fallback
            face_x, face_y, face_width, face_height = max(faces, key=lambda face: face[2] * face[3])
            torso_width = min(base.width - 8, max(int(face_width * 3.2), int(base.width * .42)))
            torso_height = min(base.height - 8, max(int(face_height * 4.2), int(base.height * .40)))
            left = max(4, min(base.width - torso_width - 4, int(face_x + face_width / 2 - torso_width / 2)))
            top = max(4, min(base.height - torso_height - 4, int(face_y + face_height * .90)))
            return (left, top, torso_width, torso_height)
        except Exception:
            return fallback

    @staticmethod
    def _prepare_alpha(garment: Image.Image) -> Image.Image:
        # Preserve a real PNG alpha channel. Near-white removal remains only
        # for opaque catalogue images such as JPGs.
        alpha = garment.getchannel("A")
        if alpha.getextrema()[0] < 255:
            return garment
        rgb = garment.convert("RGB")
        pale = rgb.point(lambda value: 255 if value > 238 else 0)
        background = ImageChops.multiply(ImageChops.multiply(pale.split()[0], pale.split()[1]), pale.split()[2])
        garment.putalpha(ImageChops.subtract(alpha, background))
        return garment

    def render(self, person: bytes, garment_path: Path) -> bytes:
        with Image.open(BytesIO(person)) as source, Image.open(garment_path) as garment_source:
            base = ImageOps.exif_transpose(source).convert("RGBA")
            garment = ImageOps.exif_transpose(garment_source).convert("RGBA")
            garment = self._prepare_alpha(garment)
            left, top, torso_width, torso_height = self._estimate_torso(base)
            # Tall garments are positioned from the lower torso. This is a
            # visual approximation, never a claim of physical simulation.
            is_bottom = garment.height > garment.width * 1.45
            target_height = int(torso_height * (1.6 if is_bottom else 1.0))
            target_width = int(torso_width * (.90 if is_bottom else 1.05))
            garment.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            if is_bottom:
                top += int(torso_height * .62)
            left += (torso_width - garment.width) // 2
            top = min(max(0, top), max(0, base.height - garment.height))
            base.alpha_composite(garment, (left, top))
            output = BytesIO()
            base.convert("RGB").save(output, format="PNG", optimize=True)
            return output.getvalue()


class ExternalVirtualTryOnProvider(VirtualTryOnProvider):
    """Reserved adapter boundary for FASHN/Replicate; no key is embedded here."""

    def render(self, person: bytes, garment_path: Path) -> bytes:
        raise NotImplementedError("El proveedor externo de vestidor virtual no está configurado")


class VirtualTryOnService:
    def __init__(self, provider: VirtualTryOnProvider | None = None) -> None:
        self.provider = provider or LocalTryOnProvider()

    def render(self, person: bytes, garment_path: Path) -> bytes:
        return self.provider.render(person, garment_path)
