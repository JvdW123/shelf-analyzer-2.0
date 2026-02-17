"""
modules/image_processor.py — Image resizing and compression.

Resizes photos to fit within Claude's max processing resolution (1568px)
and compresses as JPEG to reduce upload payload size.

Claude downscales images larger than 1568px internally anyway,
so doing it client-side saves upload bandwidth without any quality loss.
"""

import io
from PIL import Image
from config import IMAGE_CONFIG


def resize_image(image_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """
    Resize and compress an image for optimal Claude API transmission.

    - If the longest side exceeds IMAGE_CONFIG["max_dimension"], resize proportionally.
    - Always outputs JPEG (converts PNG/RGBA to RGB first).
    - Compresses with IMAGE_CONFIG["jpeg_quality"].

    Args:
        image_bytes: Raw image bytes from the file uploader
        filename: Original filename (used for logging only)

    Returns:
        Tuple of (processed_bytes, media_type)
        media_type is always "image/jpeg" after processing
    """
    max_dim = IMAGE_CONFIG["max_dimension"]
    quality = IMAGE_CONFIG["jpeg_quality"]

    img = Image.open(io.BytesIO(image_bytes))
    original_w, original_h = img.size

    # Determine if resizing is needed
    longest_side = max(original_w, original_h)
    resized = False

    if longest_side > max_dim:
        scale = max_dim / longest_side
        new_w = int(original_w * scale)
        new_h = int(original_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        resized = True

    # Convert RGBA/P to RGB (required for JPEG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Compress to JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    processed_bytes = buffer.getvalue()

    return processed_bytes, "image/jpeg"
