"""Photo validation and re-encoding.

Every upload is decoded and re-encoded as a fresh JPEG. This
- rejects anything that is not really an image (file signature + full decode),
- strips EXIF/metadata (GPS location, device serials) — a privacy requirement,
- neutralises payloads hidden in image containers.
A malware scanner (e.g. ClamAV) plugs in before this step in production (PRD §8.1).
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.common.errors import AppError

# Decompression-bomb guard: refuse images above ~40 megapixels.
Image.MAX_IMAGE_PIXELS = 40_000_000

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIN_SIDE = 300
FULL_MAX = 1600
THUMB_MAX = 480


class InvalidImage(AppError):
    status_code = 422
    code = "invalid_image"
    message = "Please upload a clear JPG, PNG or WebP photo."


@dataclass(frozen=True)
class ProcessedPhoto:
    full: bytes
    thumb: bytes
    width: int
    height: int


def sniff(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _encode(img: Image.Image, max_side: int) -> bytes:
    copy = img.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    copy.save(out, format="JPEG", quality=85, optimize=True, progressive=True)
    return out.getvalue()


def process(data: bytes, declared_type: str) -> ProcessedPhoto:
    actual = sniff(data)
    if actual is None or actual not in ALLOWED_CONTENT_TYPES or actual != declared_type:
        raise InvalidImage()
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        img: Image.Image = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise InvalidImage() from exc

    img = ImageOps.exif_transpose(img) or img  # apply camera rotation, then drop EXIF
    if img.mode not in ("RGB", "L"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    elif img.mode == "L":
        img = img.convert("RGB")

    if min(img.size) < MIN_SIDE:
        raise InvalidImage(
            "This photo is too small. Please use one at least 300 pixels wide.",
            code="image_too_small",
        )
    full = _encode(img, FULL_MAX)
    thumb = _encode(img, THUMB_MAX)
    with Image.open(io.BytesIO(full)) as done:
        width, height = done.size
    return ProcessedPhoto(full=full, thumb=thumb, width=width, height=height)
