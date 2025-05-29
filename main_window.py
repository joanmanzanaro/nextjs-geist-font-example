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
import hashlib
from typing import Optional, List, Dict, Any
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from db_manager import DBManager, DBError
from reference_service import ReferenceService
from watermark_service import WatermarkService
from social_media_service import SocialMediaService

CONFIG_FILE = "config.json"

class ImageCache:
    """Cache for storing frequently accessed image previews."""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []

    def get(self, path: str) -> Optional[QPixmap]:
        if path in self.cache:
            self._update_access(path)
            return self.cache[path]
        return None

    def put(self, path: str, pixmap: QPixmap) -> None:
        if len(self.cache) >= self.max_size:
            self._evict()
        self.cache[path] = pixmap
        self._update_access(path)

    def _update_access(self, path: str) -> None:
        if path in self.access_order:
            self.access_order.remove(path)
        self.access_order.append(path)

    def _evict(self) -> None:
        if self.access_order:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]

class MainWindow(QMainWindow):
    """Main application window for the Photo Gallery application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize services
        try:
            self.db_manager = DBManager()
            self.reference_service = ReferenceService()
            self.watermark_service = WatermarkService()
            self.social_media_service = None
        except DBError as e:
            QMessageBox.critical(self, "Database Error", str(e))
            sys.exit(1)
        
        # Initialize image cache
        self.image_cache = ImageCache()
        
        # Initialize preview timer for delayed loading
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.load_preview)
        self.current_preview_path = None
        
        # Set up UI
        self._setup_ui()
        self._setup_shortcuts()
        self.load_config()
        
        print("Window initialized successfully")

    def _setup_ui(self) -> None:
        """Set up the main user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Add search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search images by name, tags, or metadata...")
        self.search_input.textChanged.connect(self.handle_search)
        
        self.search_type = QComboBox()
        self.search_type.addItems(["All", "Filename", "Tags", "Metadata"])
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_type)
        main_layout.addLayout(search_layout)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        main_layout.addWidget(self.tabs)

        # Add tabs
        self._setup_import_tab()
        self._setup_database_tab()
        self._setup_view_tab()
        self._setup_overview_tab()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self.search_input.setFocus())
        QShortcut(QKeySequence("Esc"), self).activated.connect(
            lambda: self.search_input.clear())

    def _setup_import_tab(self) -> None:
        """Set up the Import Images tab."""
        import_tab = QWidget()
        layout = QVBoxLayout(import_tab)
        
        # File type filter
        filter_layout = QHBoxLayout()
        self.file_type_filter = QComboBox()
        self.file_type_filter.addItems([
            "All Images (*.png *.jpg *.jpeg *.bmp)",
            "PNG Files (*.png)",
            "JPEG Files (*.jpg *.jpeg)",
            "BMP Files (*.bmp)"
        ])
        filter_layout.addWidget(QLabel("File Type:"))
        filter_layout.addWidget(self.file_type_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Import list
        self.import_list = QListWidget()
        self.import_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.import_list.setAcceptDrops(True)
        layout.addWidget(self.import_list)

        # Import button
        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        layout.addWidget(import_btn)

        self.tabs.addTab(import_tab, "Import Images")

    def _setup_database_tab(self) -> None:
        """Set up the Image Database tab."""
        db_tab = QWidget()
        layout = QVBoxLayout(db_tab)

        # Database table
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["ID", "File Path", "Reference Code", "Tags"])
        self.db_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.db_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.db_table)

        self.tabs.addTab(db_tab, "Image Database")

    def _setup_view_tab(self) -> None:
        """Set up the View Images tab."""
        view_tab = QWidget()
        layout = QVBoxLayout(view_tab)

        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_label)

        # Metadata tree
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        layout.addWidget(self.metadata_tree)

        self.tabs.addTab(view_tab, "View Images")

    def _setup_overview_tab(self) -> None:
        """Set up the Overview tab."""
        overview_tab = QWidget()
        layout = QVBoxLayout(overview_tab)

        # Statistics
        stats_group = QFrame()
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel()
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_group)

        # Recent operations
        self.operations_list = QListWidget()
        layout.addWidget(self.operations_list)

        self.tabs.addTab(overview_tab, "Overview")

    def load_config(self) -> None:
        """Load application configuration from file."""
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.social_media_service = SocialMediaService(
                    access_token=config.get("instagram_token", ""),
                    instagram_account_id=config.get("instagram_account_id", "")
                )
        except FileNotFoundError:
            self.social_media_service = SocialMediaService(access_token="", instagram_account_id="")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Configuration Error", "Invalid configuration file format")
        
        self.refresh_db_table()

    def compute_md5(self, file_path: str) -> str:
        """Compute MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def handle_search(self, text: str) -> None:
        """Handle search input changes."""
        if not text:
            self.refresh_db_table()
            return

        try:
            images = self.db_manager.search_images(text, self.search_type.currentText().lower())
            self.update_table_with_images(images)
        except DBError as e:
            QMessageBox.warning(self, "Search Error", str(e))

    def import_images(self) -> None:
        """Import images from file system."""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self, 
            "Select Images",
            "",
            self.file_type_filter.currentText()
        )
        
        if not file_paths:
            return

        progress = QProgressDialog("Importing images...", "Cancel", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        for i, path in enumerate(file_paths):
            if progress.wasCanceled():
                break
                
            try:
                md5 = self.compute_md5(path)
                if not self.db_manager.get_image_by_md5(md5):
                    ref_code = self.reference_service.generate_ordered_code()
                    self.db_manager.add_image(path, md5, ref_code)
                    self.log_operation(f"Imported: {os.path.basename(path)}")
            except Exception as e:
                self.log_operation(f"Error importing {path}: {str(e)}")
            
            progress.setValue(i + 1)
        
        self.refresh_db_table()

    def refresh_db_table(self) -> None:
        """Refresh the database table view."""
        try:
            images = self.db_manager.get_all_images_with_tags()
            self.update_table_with_images([img for img, _ in images])
        except DBError as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def update_table_with_images(self, images: List[Dict[str, Any]]) -> None:
        """Update the database table with image data."""
        self.db_table.setRowCount(len(images))
        for row, image in enumerate(images):
            self.db_table.setItem(row, 0, QTableWidgetItem(str(image['id'])))
            self.db_table.setItem(row, 1, QTableWidgetItem(
                image['project_path'] or image.get('locations', [''])[0]
            ))
            self.db_table.setItem(row, 2, QTableWidgetItem(image['reference_code']))
            tags = self.db_manager.get_tags_for_image(image['id'])
            self.db_table.setItem(row, 3, QTableWidgetItem(", ".join(tags)))

    def log_operation(self, message: str) -> None:
        """Log an operation with timestamp."""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.operations_list.insertItem(0, f"{timestamp}: {message}")
        self.update_stats()

    def update_stats(self) -> None:
        """Update statistics display."""
        try:
            total_images = self.db_table.rowCount()
            tagged_images = sum(1 for row in range(total_images) 
                              if self.db_table.item(row, 3).text().strip())
            recent_ops = self.operations_list.count()
            
            stats = (f"Total Images: {total_images}\n"
                    f"Tagged Images: {tagged_images}\n"
                    f"Recent Operations: {recent_ops}")
            
            self.stats_label.setText(stats)
        except Exception as e:
            self.status_bar.showMessage(f"Error updating stats: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
