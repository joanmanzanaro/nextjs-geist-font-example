print("Testing imports...")

print("Testing PyQt6...")
from PyQt6.QtWidgets import QApplication, QMainWindow
print("PyQt6 imported successfully")

print("Testing PIL...")
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
print("PIL imported successfully")

print("Testing local modules...")
from db_manager import DBManager
print("DBManager imported successfully")
from reference_service import ReferenceService
print("ReferenceService imported successfully")
from watermark_service import WatermarkService
print("WatermarkService imported successfully")
from social_media_service import SocialMediaService
print("SocialMediaService imported successfully")

print("All imports successful")
