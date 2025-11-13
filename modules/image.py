# warehouse_app/modules/image.py
import os
from PIL import Image
from config.settings import IMAGE_LABEL_SIZE, DEFAULT_IMAGE_PATH
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


async def get_image_folder(group_name: str):
    return await get_image_folder(group_name)


async def save_image(group_name: str, component_id: str, source_path: str) -> str:
    folder = await get_image_folder(group_name)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, f"{component_id}.jpg")
    with Image.open(source_path) as img:
        img.convert("RGB").save(target, "JPEG", quality=90)
    return target


def load_image(component_id: str, group_name: str, label):
    path = os.path.join(get_image_folder(group_name), f"{component_id}.jpg")
    if os.path.exists(path):
        label.setPixmap(QPixmap(path).scaled(
            *IMAGE_LABEL_SIZE, Qt.KeepAspectRatio))
    else:
        label.setPixmap(QPixmap(DEFAULT_IMAGE_PATH).scaled(
            *IMAGE_LABEL_SIZE, Qt.KeepAspectRatio))
