import os
os.environ['QT_QPA_PLATFORM'] = 'minimal'

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
                             QFileDialog, QLabel, QLineEdit, QSlider, QHBoxLayout, QTextEdit, QMessageBox,
                             QMenuBar, QMenu, QDialog, QFormLayout, QDialogButtonBox,
                             QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView, QTableWidget, QTableWidgetItem,
                             QInputDialog, QRadioButton, QButtonGroup, QFrame, QSplitter, QProgressDialog,
                             QTreeWidget, QTreeWidgetItem, QComboBox, QScrollArea, QCompleter, QStatusBar)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QPoint, QMimeData, QUrl, QDateTime
from PyQt6.QtGui import (QIcon, QFont, QPalette, QColor, QPixmap, QKeySequence, QDrag, QImage, 
                        QAction, QShortcut)
import sys
import shutil
import json
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from db_manager import DBManager
from reference_service import ReferenceService
from watermark_service import WatermarkService
from social_media_service import SocialMediaService

CONFIG_FILE = "config.json"

__all__ = ['MainWindow']

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize services
        self.db_manager = DBManager()
        self.reference_service = ReferenceService()
        self.watermark_service = WatermarkService()
        self.social_media_service = None
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create locations list widget
        self.locations_list = QListWidget()
        layout.addWidget(self.locations_list)
        
        # Initialize UI components
        self._setup_ui()
        self.load_config()
        
        print("Window initialized successfully")

    def _setup_ui(self):
        # Add your UI setup code here
        pass

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.social_media_service = SocialMediaService(
                    access_token=config.get("instagram_token", ""),
                    instagram_account_id=config.get("instagram_account_id", "")
                )
        except FileNotFoundError:
            self.social_media_service = SocialMediaService(access_token="", instagram_account_id="")

    def update_locations_list(self, image_path):
        try:
            self.locations_list.clear()
            md5_checksum = self.compute_md5(image_path)
            image_info = self.db_manager.get_image_by_md5(md5_checksum)
            
            if image_info and 'locations' in image_info:
                for location in image_info['locations']:
                    item = QListWidgetItem(location)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked if os.path.exists(location) 
                                     else Qt.CheckState.Unchecked)
                    self.locations_list.addItem(item)
        except Exception as e:
            print(f"Error updating locations list: {str(e)}")

    def compute_md5(self, file_path: str) -> str:
        import hashlib
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    print("Application created successfully")
    window.show()
    print("Window shown")
    sys.exit(app.exec())
