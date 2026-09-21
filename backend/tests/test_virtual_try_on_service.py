from io import BytesIO

from PIL import Image

from app.services.virtual_try_on_service import LocalTryOnProvider


def png(color: str) -> bytes:
    result = BytesIO()
    Image.new("RGB", (120, 180), color).save(result, format="PNG")
    return result.getvalue()


def test_local_provider_returns_private_png(tmp_path):
    garment = tmp_path / "catalogue-garment.png"
    garment.write_bytes(png("#183f33"))

    rendered = LocalTryOnProvider().render(png("#d6b09c"), garment)

    with Image.open(BytesIO(rendered)) as image:
        assert image.format == "PNG"
        assert image.size == (120, 180)
    # The provider only returns bytes; neither the input photo nor an output is persisted.
    assert list(tmp_path.iterdir()) == [garment]
