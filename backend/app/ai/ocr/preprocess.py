"""
Image preprocessing for OCR handwriting recognition per backend-plan.md §3.
Uses Pillow to optimize contrast, handle orientation, and resize oversized scans.
"""
import io
from PIL import Image, ImageEnhance, ImageOps


def preprocess_image(image_bytes: bytes, max_dim: int = 2400) -> bytes:
    """
    Preprocess image for optimal handwriting OCR:
    - Transpose according to EXIF orientation
    - Resize if dimensions exceed max_dim
    - Enhance contrast slightly to sharpen faint pencil / pen strokes
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Auto-orient based on EXIF tags if present
    img = ImageOps.exif_transpose(img)

    # Resize if oversized while preserving aspect ratio
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to RGB if palette / RGBA
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Gentle contrast enhancement (1.2x)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=90)
    return output.getvalue()
