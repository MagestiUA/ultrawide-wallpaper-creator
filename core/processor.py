from pathlib import Path
from PIL import Image

SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
TARGET_RATIO = 16 / 9
OUTPUT_WIDTH = 10240
OUTPUT_HEIGHT = 2880
HALF_WIDTH = OUTPUT_WIDTH // 2  # 5120


def _apply_rotation(img: Image.Image, rotation_cw: int) -> Image.Image:
    """Повертає зображення за годинниковою стрілкою на 0/90/180/270°."""
    if rotation_cw == 90:
        return img.rotate(-90, expand=True)
    elif rotation_cw == 180:
        return img.rotate(180, expand=True)
    elif rotation_cw == 270:
        return img.rotate(90, expand=True)
    return img


def get_images_from_folder(folder: Path) -> list[Path]:
    """Повертає список підтримуваних зображень з папки."""
    return sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in SUPPORTED_FORMATS
    )


def crop_to_ratio(
    img: Image.Image,
    ratio: float = TARGET_RATIO,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
) -> Image.Image:
    """
    Кропає зображення до потрібного співвідношення сторін.
    anchor_x/anchor_y: 0.0 = ліво/верх, 0.5 = центр, 1.0 = право/низ
    """
    w, h = img.size
    current_ratio = w / h

    if abs(current_ratio - ratio) < 0.01:
        return img

    if current_ratio > ratio:
        # Занадто широке — кропаємо по ширині
        new_w = int(h * ratio)
        offset = int((w - new_w) * anchor_x)
        return img.crop((offset, 0, offset + new_w, h))
    else:
        # Занадто висока — кропаємо по висоті
        new_h = int(w / ratio)
        offset = int((h - new_h) * anchor_y)
        return img.crop((0, offset, w, offset + new_h))


def resize_to_half(img: Image.Image) -> Image.Image:
    """Ресайзить до 5120x2880 (ліва або права половина)."""
    return img.resize((HALF_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS)


def combine_pair(
    left: Image.Image,
    right: Image.Image,
) -> Image.Image:
    """Склеює два зображення 5120x2880 в одне 10240x2880."""
    canvas = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (HALF_WIDTH, 0))
    return canvas


def process_pair(
    left_path: Path,
    right_path: Path,
    output_path: Path,
    left_anchor: tuple[float, float] = (0.5, 0.5),
    right_anchor: tuple[float, float] = (0.5, 0.5),
    quality: int = 95,
    left_rotation: int = 0,
    right_rotation: int = 0,
) -> Path:
    """
    Повний pipeline: відкрити → повернути → кроп → ресайз → склеїти → зберегти.
    Повертає шлях до збереженого файлу.
    """
    left_img = Image.open(left_path).convert("RGB")
    right_img = Image.open(right_path).convert("RGB")

    left_img = _apply_rotation(left_img, left_rotation)
    right_img = _apply_rotation(right_img, right_rotation)

    left_img = crop_to_ratio(left_img, anchor_x=left_anchor[0], anchor_y=left_anchor[1])
    right_img = crop_to_ratio(right_img, anchor_x=right_anchor[0], anchor_y=right_anchor[1])

    left_img = resize_to_half(left_img)
    right_img = resize_to_half(right_img)

    result = combine_pair(left_img, right_img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "JPEG", quality=quality, optimize=True)
    return output_path


def make_thumbnail(image_path: Path, size: tuple[int, int] = (200, 113)) -> Image.Image:
    """Генерує мініатюру зображення для UI (16:9 кроп + ресайз)."""
    img = Image.open(image_path).convert("RGB")
    img = crop_to_ratio(img)
    img.thumbnail(size, Image.LANCZOS)
    # Точний розмір (thumbnail зберігає пропорції)
    result = Image.new("RGB", size, (20, 20, 20))
    offset_x = (size[0] - img.width) // 2
    offset_y = (size[1] - img.height) // 2
    result.paste(img, (offset_x, offset_y))
    return result
