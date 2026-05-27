from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


@dataclass
class PreprocessResult:
    original_path: str
    preprocessed_path: str
    file_format: str
    width: int = 512
    height: int = 512
    bit_depth: int = 8
    contrast_adjusted: bool = True


async def read_validated_upload(file: UploadFile) -> tuple[bytes, str]:
    content = await file.read()
    name = (file.filename or "").lower()
    if name.endswith(".dcm") or (len(content) > 132 and content[128:132] == b"DICM"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG/JPEG accepted")
    if content.startswith(PNG_MAGIC):
        return content, "PNG"
    if content.startswith(JPEG_MAGIC):
        return content, "JPEG"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG/JPEG accepted")


def preprocess_image(content: bytes, file_format: str, case_dir: Path) -> PreprocessResult:
    case_dir.mkdir(parents=True, exist_ok=True)
    ext = "png" if file_format == "PNG" else "jpg"
    original_path = case_dir / f"original.{ext}"
    preprocessed_path = case_dir / "preprocessed.png"
    original_path.write_bytes(content)

    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("L")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid PNG/JPEG image")

    arr = np.asarray(image).astype(np.float32)
    span = float(arr.max() - arr.min())
    if span > 0:
        arr = (arr - arr.min()) / span * 255.0
    normalized = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L")
    adjusted = ImageOps.autocontrast(normalized)

    # Keep anatomy proportions stable by fitting inside 512 square and padding.
    resized = ImageOps.contain(adjusted, (512, 512), method=Image.Resampling.LANCZOS)
    canvas = Image.new("L", (512, 512), 0)
    offset = ((512 - resized.width) // 2, (512 - resized.height) // 2)
    canvas.paste(resized, offset)
    canvas.save(preprocessed_path, format="PNG")

    return PreprocessResult(
        original_path=str(original_path),
        preprocessed_path=str(preprocessed_path),
        file_format="PNG",
    )
