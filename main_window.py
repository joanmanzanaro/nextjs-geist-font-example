import sys
import os
import hashlib
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
                             QFileDialog, QLabel, QLineEdit, QSlider, QHBoxLayout, QTextEdit, QMessageBox,
                             QMenuBar, QMenu, QAction, QStatusBar, QDialog, QFormLayout, QDialogButtonBox,
                             QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView, QTableWidget, QTableWidgetItem,
                             QInputDialog, QLineEdit, QRadioButton, QButtonGroup, QFrame, QSplitter, QProgressDialog,
                             QTreeWidget, QTreeWidgetItem, QComboBox, QScrollArea, QShortcut, QCompleter)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QPoint, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QKeySequence, QDrag, QImage
import os
import shutil
from PIL import Image as PILImage
from PIL.ExifTags import TAGS
from db_manager import DBManager
from reference_service import ReferenceService
from watermark_service import WatermarkService
from social_media_service import SocialMediaService

CONFIG_FILE = "config.json"

class ImageScannerThread(QThread):
    progress = pyqtSignal(int)
    found_match = pyqtSignal(str, str)  # file_path, md5_checksum
    finished = pyqtSignal()

    def __init__(self, start_path: str, known_checksums: List[str]):
        super().__init__()
        self.start_path = start_path
        self.known_checksums = known_checksums
        self.running = True

    def run(self):
        total_files = sum([len(files) for _, _, files in os.walk(self.start_path)])
        processed = 0

        for root, _, files in os.walk(self.start_path):
            if not self.running:
                break
            
            for file in files:
                if not self.running:
                    break

                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    file_path = os.path.join(root, file)
                    try:
                        md5_checksum = self.compute_md5(file_path)
                        if md5_checksum in self.known_checksums:
                            self.found_match.emit(file_path, md5_checksum)
                    except:
                        pass  # Skip files that can't be read
                
                processed += 1
                self.progress.emit(int(processed * 100 / total_files))

        self.finished.emit()

    def stop(self):
        self.running = False

    def compute_md5(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.layout = QFormLayout(self)

        self.instagram_token_input = QLineEdit()
        self.instagram_account_id_input = QLineEdit()
        self.default_watermark_text_input = QLineEdit()
        self.default_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.default_opacity_slider.setMinimum(0)
        self.default_opacity_slider.setMaximum(100)

        self.project_folder_input = QLineEdit()
        self.project_folder_browse_button = QPushButton("Browse")
        self.project_folder_browse_button.clicked.connect(self.browse_project_folder)

        self.watermark_image_path_input = QLineEdit()
        self.watermark_image_browse_button = QPushButton("Browse")
        self.watermark_image_browse_button.clicked.connect(self.browse_watermark_image)

        self.watermark_position_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.watermark_position_x_slider.setMinimum(0)
        self.watermark_position_x_slider.setMaximum(100)

        self.watermark_position_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.watermark_position_y_slider.setMinimum(0)
        self.watermark_position_y_slider.setMaximum(100)

        self.watermark_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.watermark_scale_slider.setMinimum(1)
        self.watermark_scale_slider.setMaximum(100)

        self.layout.addRow("Instagram Access Token:", self.instagram_token_input)
        self.layout.addRow("Instagram Account ID:", self.instagram_account_id_input)
        self.layout.addRow("Default Watermark Text:", self.default_watermark_text_input)
        self.layout.addRow("Default Watermark Opacity:", self.default_opacity_slider)

        project_layout = QHBoxLayout()
        project_layout.addWidget(self.project_folder_input)
        project_layout.addWidget(self.project_folder_browse_button)
        self.layout.addRow("Project Folder:", project_layout)

        watermark_layout = QHBoxLayout()
        watermark_layout.addWidget(self.watermark_image_path_input)
        watermark_layout.addWidget(self.watermark_image_browse_button)
        self.layout.addRow("Watermark Image Path:", watermark_layout)
        self.layout.addRow("Watermark Position X (%):", self.watermark_position_x_slider)
        self.layout.addRow("Watermark Position Y (%):", self.watermark_position_y_slider)
        self.layout.addRow("Watermark Scale (% of image width):", self.watermark_scale_slider)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.load_config()

    def browse_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self.project_folder_input.setText(folder)

    def browse_watermark_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Watermark Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.watermark_image_path_input.setText(file_path)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.instagram_token_input.setText(config.get("instagram_token", ""))
                self.instagram_account_id_input.setText(config.get("instagram_account_id", ""))
                self.default_watermark_text_input.setText(config.get("default_watermark_text", ""))
                self.default_opacity_slider.setValue(int(config.get("default_opacity", 50) * 100))
                self.project_folder_input.setText(config.get("project_folder", ""))
                self.watermark_image_path_input.setText(config.get("watermark_image_path", ""))
                self.watermark_position_x_slider.setValue(int(config.get("watermark_position_x", 90) * 100))
                self.watermark_position_y_slider.setValue(int(config.get("watermark_position_y", 90) * 100))
                self.watermark_scale_slider.setValue(int(config.get("watermark_scale", 10) * 100))
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {
            "instagram_token": self.instagram_token_input.text(),
            "instagram_account_id": self.instagram_account_id_input.text(),
            "default_watermark_text": self.default_watermark_text_input.text(),
            "default_opacity": self.default_opacity_slider.value() / 100.0,
            "project_folder": self.project_folder_input.text(),
            "watermark_image_path": self.watermark_image_path_input.text(),
            "watermark_position_x": self.watermark_position_x_slider.value() / 100.0,
            "watermark_position_y": self.watermark_position_y_slider.value() / 100.0,
            "watermark_scale": self.watermark_scale_slider.value() / 100.0
        }
        
        # Create project folder if it doesn't exist
        project_folder = self.project_folder_input.text()
        if project_folder and not os.path.exists(project_folder):
            os.makedirs(project_folder)
            
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

class ScanDriveDialog(QDialog):
    def __init__(self, parent=None, known_checksums=None):
        super().__init__(parent)
        self.known_checksums = known_checksums or []
        self.scanner_thread = None
        self.matches = []
        
        self.setWindowTitle("Scan Drive for Images")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder to scan")
        folder_layout.addWidget(self.folder_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)
        
        # Progress and status
        self.progress_bar = QProgressDialog("Scanning...", "Cancel", 0, 100, self)
        self.progress_bar.setAutoClose(True)
        self.progress_bar.setAutoReset(True)
        self.progress_bar.hide()
        
        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Original Path", "Found Path", "Status"])
        self.results_tree.setColumnWidth(0, 200)
        self.results_tree.setColumnWidth(1, 200)
        layout.addWidget(self.results_tree)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_btn)
        
        self.copy_btn = QPushButton("Copy Selected to Project")
        self.copy_btn.clicked.connect(self.copy_selected)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self.folder_input.setText(folder)

    def start_scan(self):
        folder = self.folder_input.text()
        if not folder or not os.path.exists(folder):
            QMessageBox.warning(self, "Error", "Please select a valid folder to scan.")
            return

        self.results_tree.clear()
        self.matches = []
        self.scan_btn.setEnabled(False)
        self.progress_bar.show()

        self.scanner_thread = ImageScannerThread(folder, self.known_checksums)
        self.scanner_thread.progress.connect(self.progress_bar.setValue)
        self.scanner_thread.found_match.connect(self.add_match)
        self.scanner_thread.finished.connect(self.scan_finished)
        self.scanner_thread.start()

    def add_match(self, file_path: str, md5_checksum: str):
        item = QTreeWidgetItem([file_path, "", "Found"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        self.results_tree.addTopLevelItem(item)
        self.matches.append((file_path, md5_checksum))

    def scan_finished(self):
        self.scan_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.progress_bar.hide()
        
        count = len(self.matches)
        QMessageBox.information(self, "Scan Complete", 
                              f"Found {count} matching image{'s' if count != 1 else ''}.")

    def copy_selected(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                project_folder = config.get("project_folder")
        except:
            QMessageBox.warning(self, "Error", "Project folder not configured.")
            return

        if not project_folder:
            QMessageBox.warning(self, "Error", "Project folder not configured.")
            return

        copied = 0
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                source_path = item.text(0)
                if not os.path.exists(source_path):
                    continue

                filename = os.path.basename(source_path)
                dest_path = os.path.join(project_folder, filename)
                
                try:
                    shutil.copy2(source_path, dest_path)
                    md5_checksum = self.parent().compute_md5(source_path)
                    image_info = self.parent().db_manager.get_image_by_md5(md5_checksum)
                    
                    if image_info:
                        self.parent().db_manager.add_image_location(image_info['id'], dest_path, True)
                        self.parent().db_manager.set_project_path(image_info['id'], dest_path)
                    
                    item.setText(1, dest_path)
                    item.setText(2, "Copied")
                    copied += 1
                except Exception as e:
                    item.setText(2, f"Error: {str(e)}")

        QMessageBox.information(self, "Copy Complete", 
                              f"Copied {copied} image{'s' if copied != 1 else ''} to project folder.")

class ImageCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []

    def get(self, path):
        if path in self.cache:
            self._update_access(path)
            return self.cache[path]
        return None

    def put(self, path, pixmap):
        if len(self.cache) >= self.max_size:
            self._evict()
        self.cache[path] = pixmap
        self._update_access(path)

    def _update_access(self, path):
        if path in self.access_order:
            self.access_order.remove(path)
        self.access_order.append(path)

    def _evict(self):
        if self.access_order:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]

class MetadataEditDialog(QDialog):
    def __init__(self, parent=None, metadata=None, batch_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Metadata" if not batch_mode else "Batch Edit Metadata")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Metadata tree
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        self.metadata_tree.setColumnWidth(0, 200)
        layout.addWidget(self.metadata_tree)
        
        # Populate existing metadata
        if metadata:
            for key, value in metadata.items():
                item = QTreeWidgetItem([key, str(value)])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.metadata_tree.addTopLevelItem(item)
        
        # Controls
        controls = QHBoxLayout()
        
        add_btn = QPushButton("Add Property")
        add_btn.clicked.connect(self.add_property)
        controls.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Property")
        remove_btn.clicked.connect(self.remove_property)
        controls.addWidget(remove_btn)
        
        layout.addLayout(controls)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_property(self):
        item = QTreeWidgetItem(["New Property", "Value"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.metadata_tree.addTopLevelItem(item)
        self.metadata_tree.editItem(item, 0)

    def remove_property(self):
        current = self.metadata_tree.currentItem()
        if current:
            self.metadata_tree.takeTopLevelItem(
                self.metadata_tree.indexOfTopLevelItem(current)
            )

    def get_metadata(self):
        metadata = {}
        for i in range(self.metadata_tree.topLevelItemCount()):
            item = self.metadata_tree.topLevelItem(i)
            key = item.text(0)
            value = item.text(1)
            if key and value:
                metadata[key] = value
        return metadata

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery and Tag Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize image cache
        self.image_cache = ImageCache()
        
        # Initialize preview timer for delayed loading
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.load_preview)
        self.current_preview_path = None

        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #e1e1e1;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
            QLineEdit, QTextEdit {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background: white;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background: white;
                gridline-color: #e1e1e1;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background: white;
            }
            QListWidget::item {
                padding: 4px;
            }
            QStatusBar {
                background: #f0f0f0;
                color: #333333;
            }
        """)

        # Initialize services
        self.db_manager = DBManager()
        self.reference_service = ReferenceService()
        self.watermark_service = WatermarkService()
        self.social_media_service = None

        self.selected_image_paths = []

        # Set default font
        font = QFont()
        font.setPointSize(10)
        QApplication.setFont(font)

        self._setup_ui()
        self.load_config()

    def _setup_ui(self):
        # Setup menu bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # File Menu
        file_menu = QMenu("&File", self)
        self.menu_bar.addMenu(file_menu)

        config_action = QAction(QIcon(), "Configuration", self)
        config_action.setShortcut("Ctrl+,")
        config_action.triggered.connect(self.open_config_dialog)
        file_menu.addAction(config_action)

        scan_action = QAction(QIcon(), "Scan Drive for Images", self)
        scan_action.setShortcut("Ctrl+F")
        scan_action.triggered.connect(self.open_scan_dialog)
        file_menu.addAction(scan_action)

        export_action = QAction(QIcon(), "Export Database", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_database)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction(QIcon(), "Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools Menu
        tools_menu = QMenu("&Tools", self)
        self.menu_bar.addMenu(tools_menu)

        verify_locations_action = QAction(QIcon(), "Verify Image Locations", self)
        verify_locations_action.triggered.connect(self.verify_image_locations)
        tools_menu.addAction(verify_locations_action)

        batch_metadata_action = QAction(QIcon(), "Batch Edit Metadata", self)
        batch_metadata_action.triggered.connect(self.batch_edit_metadata)
        tools_menu.addAction(batch_metadata_action)

        # Setup central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
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

        # Create tab widget with modern styling
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # More modern look
        self.tabs.setMovable(True)  # Allow tab reordering
        main_layout.addWidget(self.tabs)

        # Setup keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self.search_input.setFocus())
        QShortcut(QKeySequence("Esc"), self).activated.connect(
            lambda: self.search_input.clear())

        # Import Images Tab
        self.import_tab = QWidget()
        import_layout = QVBoxLayout()
        import_layout.setSpacing(10)

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
        import_layout.addLayout(filter_layout)

        # Top section with import button and list
        top_section = QFrame()
        top_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        top_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        self.import_button = QPushButton("Import Images")
        self.import_button.setIcon(QIcon())  # Add icon here
        self.import_button.clicked.connect(self.import_images)
        header_layout.addWidget(self.import_button)
        header_layout.addStretch()
        top_layout.addLayout(header_layout)

        self.import_list = QListWidget()
        self.import_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.import_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.import_list.customContextMenuRequested.connect(self.show_import_context_menu)
        self.import_list.setAcceptDrops(True)
        self.import_list.dragEnterEvent = self.dragEnterEvent
        self.import_list.dropEvent = self.dropEvent
        top_layout.addWidget(self.import_list)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self._is_valid_image_file(file_path):
                files.append(file_path)
        
        if files:
            self.process_imported_files(files)
            
    def _is_valid_image_file(self, file_path):
        current_filter = self.file_type_filter.currentText()
        ext = os.path.splitext(file_path)[1].lower()
        
        if current_filter == "All Images (*.png *.jpg *.jpeg *.bmp)":
            return ext in ['.png', '.jpg', '.jpeg', '.bmp']
        elif current_filter == "PNG Files (*.png)":
            return ext == '.png'
        elif current_filter == "JPEG Files (*.jpg *.jpeg)":
            return ext in ['.jpg', '.jpeg']
        elif current_filter == "BMP Files (*.bmp)":
            return ext == '.bmp'
        return False

    def process_imported_files(self, file_paths):
        self.import_list.clear()
        for file_path in file_paths:
            if self._is_valid_image_file(file_path):
                item = QListWidgetItem(file_path)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.import_list.addItem(item)

        top_section.setLayout(top_layout)
        import_layout.addWidget(top_section)

        # Watermark section
        watermark_section = QFrame()
        watermark_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        watermark_layout = QVBoxLayout()

        # Watermark mode selection
        mode_label = QLabel("Watermark Type:")
        mode_label.setStyleSheet("font-weight: bold;")
        watermark_layout.addWidget(mode_label)

        self.watermark_mode_group = QButtonGroup(self)
        mode_buttons_layout = QHBoxLayout()
        self.text_watermark_radio = QRadioButton("Text Watermark")
        self.image_watermark_radio = QRadioButton("Image Watermark")
        self.text_watermark_radio.setChecked(True)
        self.watermark_mode_group.addButton(self.text_watermark_radio)
        self.watermark_mode_group.addButton(self.image_watermark_radio)
        mode_buttons_layout.addWidget(self.text_watermark_radio)
        mode_buttons_layout.addWidget(self.image_watermark_radio)
        mode_buttons_layout.addStretch()
        watermark_layout.addLayout(mode_buttons_layout)

        # Text watermark input
        text_label = QLabel("Watermark Text:")
        text_label.setStyleSheet("font-weight: bold;")
        watermark_layout.addWidget(text_label)
        self.watermark_text_input = QLineEdit()
        self.watermark_text_input.setPlaceholderText("Enter watermark text")
        watermark_layout.addWidget(self.watermark_text_input)

        # Opacity control
        opacity_label = QLabel("Opacity:")
        opacity_label.setStyleSheet("font-weight: bold;")
        watermark_layout.addWidget(opacity_label)
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_value = QLabel("50%")
        self.opacity_slider.valueChanged.connect(lambda v: opacity_value.setText(f"{v}%"))
        opacity_layout.addWidget(opacity_value)
        watermark_layout.addLayout(opacity_layout)

        # Apply button
        self.apply_watermark_button = QPushButton("Apply Watermark")
        self.apply_watermark_button.setIcon(QIcon())  # Add icon here
        self.apply_watermark_button.clicked.connect(self.apply_watermark_batch)
        watermark_layout.addWidget(self.apply_watermark_button)

        watermark_section.setLayout(watermark_layout)
        import_layout.addWidget(watermark_section)

        # Share section
        share_section = QFrame()
        share_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        share_layout = QVBoxLayout()

        share_label = QLabel("Share on Instagram:")
        share_label.setStyleSheet("font-weight: bold;")
        share_layout.addWidget(share_label)

        self.share_caption_input = QTextEdit()
        self.share_caption_input.setPlaceholderText("Enter caption for Instagram")
        self.share_caption_input.setMaximumHeight(100)
        share_layout.addWidget(self.share_caption_input)

        self.share_button = QPushButton("Share")
        self.share_button.setIcon(QIcon())  # Add icon here
        self.share_button.clicked.connect(self.share_on_instagram)
        share_layout.addWidget(self.share_button)

        share_section.setLayout(share_layout)
        import_layout.addWidget(share_section)

        self.import_tab.setLayout(import_layout)
        self.tabs.addTab(self.import_tab, "Import Images")

        # Database Viewer Tab
        self.db_tab = QWidget()
        db_layout = QVBoxLayout()
        db_layout.setSpacing(10)

        # Database controls section
        controls_section = QFrame()
        controls_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        controls_layout = QHBoxLayout()

        self.edit_tags_button = QPushButton("Edit Tags")
        self.edit_tags_button.setIcon(QIcon())  # Add icon here
        self.edit_tags_button.clicked.connect(self.edit_tags)
        controls_layout.addWidget(self.edit_tags_button)

        self.delete_image_button = QPushButton("Delete Image")
        self.delete_image_button.setIcon(QIcon())  # Add icon here
        self.delete_image_button.clicked.connect(self.delete_image)
        controls_layout.addWidget(self.delete_image_button)

        controls_layout.addStretch()
        controls_section.setLayout(controls_layout)
        db_layout.addWidget(controls_section)

        # Database table section
        table_section = QFrame()
        table_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        table_layout = QVBoxLayout()

        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["ID", "File Path", "Reference Code", "Tags"])
        self.db_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.db_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.db_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.db_table.customContextMenuRequested.connect(self.show_db_context_menu)
        self.db_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.db_table)

        table_section.setLayout(table_layout)
        db_layout.addWidget(table_section)

        self.db_tab.setLayout(db_layout)
        self.tabs.addTab(self.db_tab, "Image Database")

        # Overview Tab
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout()
        overview_layout.setSpacing(10)

        # Stats section
        stats_section = QFrame()
        stats_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        stats_layout = QVBoxLayout()

        stats_title = QLabel("Statistics")
        stats_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(stats_title)

        self.stats_content = QLabel()
        self.stats_content.setStyleSheet("padding: 10px;")
        stats_layout.addWidget(self.stats_content)

        stats_section.setLayout(stats_layout)
        overview_layout.addWidget(stats_section)

        # Recent Operations section
        operations_section = QFrame()
        operations_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        operations_layout = QVBoxLayout()

        operations_title = QLabel("Recent Operations")
        operations_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        operations_layout.addWidget(operations_title)

        self.operations_list = QListWidget()
        operations_layout.addWidget(self.operations_list)

        operations_section.setLayout(operations_layout)
        overview_layout.addWidget(operations_section)

        self.overview_tab.setLayout(overview_layout)
        self.tabs.addTab(self.overview_tab, "Overview")

        # View Images Tab
        self.view_tab = QWidget()
        view_layout = QVBoxLayout()
        view_layout.setSpacing(10)

        # Split view for preview and metadata
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Preview section
        preview_section = QFrame()
        preview_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        preview_layout = QVBoxLayout()
        preview_section.setLayout(preview_layout)

        preview_title = QLabel("Image Preview")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        preview_layout.addWidget(preview_title)

        self.view_image_label = QLabel("Select an image to preview changes.")
        self.view_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view_image_label.setStyleSheet("background-color: #f0f0f0; padding: 20px; border-radius: 4px;")
        self.view_image_label.setMinimumHeight(300)
        preview_layout.addWidget(self.view_image_label)

        # Image locations list
        locations_title = QLabel("Image Locations")
        locations_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        preview_layout.addWidget(locations_title)

        self.locations_list = QListWidget()
        preview_layout.addWidget(self.locations_list)

        copy_to_project_btn = QPushButton("Copy to Project Folder")
        copy_to_project_btn.clicked.connect(self.copy_to_project_folder)
        preview_layout.addWidget(copy_to_project_btn)

        # Right side - Metadata section
        metadata_section = QFrame()
        metadata_section.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        metadata_layout = QVBoxLayout()
        metadata_section.setLayout(metadata_layout)

        metadata_title = QLabel("Metadata")
        metadata_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        metadata_layout.addWidget(metadata_title)

        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        self.metadata_tree.setColumnWidth(0, 200)
        metadata_layout.addWidget(self.metadata_tree)

        metadata_controls = QHBoxLayout()
        
        self.edit_metadata_btn = QPushButton("Edit Metadata")
        self.edit_metadata_btn.clicked.connect(self.edit_metadata)
        metadata_controls.addWidget(self.edit_metadata_btn)
        
        self.batch_metadata_btn = QPushButton("Batch Edit Metadata")
        self.batch_metadata_btn.clicked.connect(self.batch_edit_metadata)
        metadata_controls.addWidget(self.batch_metadata_btn)
        
        metadata_layout.addLayout(metadata_controls)

        # Add sections to splitter
        splitter.addWidget(preview_section)
        splitter.addWidget(metadata_section)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        view_layout.addWidget(splitter)
        self.view_tab.setLayout(view_layout)
        self.tabs.addTab(self.view_tab, "View Images")

        central_widget.setLayout(main_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.social_media_service = SocialMediaService(
                    access_token=config.get("instagram_token", ""),
                    instagram_account_id=config.get("instagram_account_id", "")
                )
                self.watermark_text_input.setText(config.get("default_watermark_text", ""))
                self.opacity_slider.setValue(int(config.get("default_opacity", 0.5) * 100))
                self.status_bar.showMessage("Configuration loaded.")
                self.refresh_db_table()
        except FileNotFoundError:
            self.social_media_service = SocialMediaService(access_token="", instagram_account_id="")
            self.status_bar.showMessage("No configuration file found. Using defaults.")

    def show_import_context_menu(self, position):
        menu = QMenu()
        select_all = menu.addAction("Select All")
        deselect_all = menu.addAction("Deselect All")
        menu.addSeparator()
        preview = menu.addAction("Preview")
        
        action = menu.exec(self.import_list.mapToGlobal(position))
        if action == select_all:
            for i in range(self.import_list.count()):
                self.import_list.item(i).setCheckState(Qt.CheckState.Checked)
        elif action == deselect_all:
            for i in range(self.import_list.count()):
                self.import_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        elif action == preview:
            selected_items = self.import_list.selectedItems()
            if selected_items:
                self.preview_image(selected_items[0].text())
                self.tabs.setCurrentWidget(self.view_tab)

    def show_db_context_menu(self, position):
        menu = QMenu()
        preview = menu.addAction("Preview")
        edit_tags = menu.addAction("Edit Tags")
        menu.addSeparator()
        delete = menu.addAction("Delete")
        
        action = menu.exec(self.db_table.mapToGlobal(position))
        if action == preview:
            selected_rows = self.db_table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                file_path = self.db_table.item(row, 1).text()
                self.preview_image(file_path)
                self.tabs.setCurrentWidget(self.view_tab)
        elif action == edit_tags:
            self.edit_tags()
        elif action == delete:
            self.delete_image()

    def handle_search(self, text):
        if not text:
            self.refresh_db_table()
            return

        search_type = self.search_type.currentText()
        cursor = self.db_manager.conn.cursor()

        if search_type == "All":
            cursor.execute("""
                SELECT DISTINCT i.* FROM images i
                LEFT JOIN image_locations il ON i.id = il.image_id
                LEFT JOIN image_tags it ON i.id = it.image_id
                LEFT JOIN tags t ON it.tag_id = t.id
                WHERE il.file_path LIKE ? 
                OR t.name LIKE ?
                OR i.metadata LIKE ?
            """, (f"%{text}%", f"%{text}%", f"%{text}%"))
        elif search_type == "Filename":
            cursor.execute("""
                SELECT DISTINCT i.* FROM images i
                JOIN image_locations il ON i.id = il.image_id
                WHERE il.file_path LIKE ?
            """, (f"%{text}%",))
        elif search_type == "Tags":
            cursor.execute("""
                SELECT DISTINCT i.* FROM images i
                JOIN image_tags it ON i.id = it.image_id
                JOIN tags t ON it.tag_id = t.id
                WHERE t.name LIKE ?
            """, (f"%{text}%",))
        else:  # Metadata
            cursor.execute("""
                SELECT * FROM images
                WHERE metadata LIKE ?
            """, (f"%{text}%",))

        images = cursor.fetchall()
        self.db_table.setRowCount(len(images))
        for row, image in enumerate(images):
            tags = self.db_manager.get_tags_for_image(image['id'])
            self.db_table.setItem(row, 0, QTableWidgetItem(str(image['id'])))
            self.db_table.setItem(row, 1, QTableWidgetItem(
                image['project_path'] if image['project_path'] else 
                (image['locations'][0] if image['locations'] else "No location")
            ))
            self.db_table.setItem(row, 2, QTableWidgetItem(image['reference_code']))
            self.db_table.setItem(row, 3, QTableWidgetItem(", ".join(tags)))

    def preview_image(self, image_path):
        if not image_path:
            return

        self.current_preview_path = image_path
        
        # Check cache first
        cached_pixmap = self.image_cache.get(image_path)
        if cached_pixmap:
            self.view_image_label.setPixmap(cached_pixmap)
            self.load_image_metadata(image_path)
            self.update_locations_list(image_path)
            return

        # Start preview timer to delay loading for better UI responsiveness
        self.preview_timer.start(100)

    def load_preview(self):
        if not self.current_preview_path:
            return

        try:
            # Load and scale image
            pixmap = QPixmap(self.current_preview_path)
            scaled_pixmap = pixmap.scaled(
                self.view_image_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Cache the scaled pixmap
            self.image_cache.put(self.current_preview_path, scaled_pixmap)
            
            # Update UI
            self.view_image_label.setPixmap(scaled_pixmap)
            self.load_image_metadata(self.current_preview_path)
            self.update_locations_list(self.current_preview_path)
            
        except Exception as e:
            self.status_bar.showMessage(f"Error previewing image: {str(e)}")
            self.view_image_label.setText("Error loading image")

    def load_image_metadata(self, image_path):
        self.metadata_tree.clear()
        try:
            with PILImage.open(image_path) as img:
                # Basic image info
                info_item = QTreeWidgetItem(["Image Info"])
                self.metadata_tree.addTopLevelItem(info_item)
                info_item.addChild(QTreeWidgetItem(["Format", img.format]))
                info_item.addChild(QTreeWidgetItem(["Size", f"{img.width} x {img.height}"]))
                info_item.addChild(QTreeWidgetItem(["Mode", img.mode]))
                
                # EXIF data
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    exif_item = QTreeWidgetItem(["EXIF Data"])
                    self.metadata_tree.addTopLevelItem(exif_item)
                    
                    for tag_id in exif:
                        try:
                            tag = TAGS.get(tag_id, tag_id)
                            value = str(exif[tag_id])
                            exif_item.addChild(QTreeWidgetItem([tag, value]))
                        except:
                            continue

    def update_locations_list(self, image_path):
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

    def copy_to_project_folder(self):
        selected_items = self.import_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No images selected to copy.")
            return

        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                project_folder = config.get("project_folder")
        except:
            self.status_bar.showMessage("Project folder not configured.")
            return

        if not project_folder:
            self.status_bar.showMessage("Project folder not configured.")
            return

        for item in selected_items:
            source_path = item.text()
            if not os.path.exists(source_path):
                continue

            filename = os.path.basename(source_path)
            dest_path = os.path.join(project_folder, filename)
            
            try:
                shutil.copy2(source_path, dest_path)
                md5_checksum = self.compute_md5(source_path)
                image_info = self.db_manager.get_image_by_md5(md5_checksum)
                
                if image_info:
                    self.db_manager.add_image_location(image_info['id'], dest_path, True)
                    self.db_manager.set_project_path(image_info['id'], dest_path)
                
                self.log_operation(f"Copied {filename} to project folder")
                self.status_bar.showMessage(f"Copied {filename} to project folder")
            except Exception as e:
                self.status_bar.showMessage(f"Error copying {filename}: {str(e)}")

    def edit_metadata(self):
        selected_items = self.import_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("No image selected for metadata editing.")
            return

        file_path = selected_items[0].text()
        try:
            # Get existing metadata
            md5_checksum = self.compute_md5(file_path)
            image_info = self.db_manager.get_image_by_md5(md5_checksum)
            
            if not image_info:
                self.status_bar.showMessage("Image not found in database.")
                return
                
            # Open edit dialog
            dialog = MetadataEditDialog(self, image_info.get('metadata', {}))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_metadata = dialog.get_metadata()
                self.db_manager.update_image_metadata(image_info['id'], new_metadata)
                self.status_bar.showMessage("Metadata updated successfully.")
                self.log_operation(f"Updated metadata for {os.path.basename(file_path)}")
                self.refresh_db_table()
                
        except Exception as e:
            self.status_bar.showMessage(f"Error updating metadata: {str(e)}")

    def batch_edit_metadata(self):
        checked_items = [self.import_list.item(i) for i in range(self.import_list.count()) 
                        if self.import_list.item(i).checkState() == Qt.CheckState.Checked]
        if not checked_items:
            self.status_bar.showMessage("No images selected for batch metadata editing.")
            return

        # Open batch edit dialog
        dialog = MetadataEditDialog(self, batch_mode=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_metadata = dialog.get_metadata()
            
            progress = QProgressDialog(
                "Updating metadata...", "Cancel", 0, len(checked_items), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            
            updated = 0
            errors = 0
            
            for i, item in enumerate(checked_items):
                if progress.wasCanceled():
                    break
                    
                try:
                    file_path = item.text()
                    md5_checksum = self.compute_md5(file_path)
                    image_info = self.db_manager.get_image_by_md5(md5_checksum)
                    
                    if image_info:
                        # Merge new metadata with existing
                        existing_metadata = image_info.get('metadata', {})
                        existing_metadata.update(new_metadata)
                        self.db_manager.update_image_metadata(
                            image_info['id'], existing_metadata)
                        updated += 1
                except Exception as e:
                    errors += 1
                    self.log_operation(
                        f"Error updating metadata for {os.path.basename(file_path)}: {str(e)}")
                
                progress.setValue(i + 1)
            
            status_msg = f"Updated metadata for {updated} images"
            if errors:
                status_msg += f" ({errors} errors)"
            self.status_bar.showMessage(status_msg)
            self.log_operation(status_msg)
            self.refresh_db_table()

    def log_operation(self, operation):
        self.operations_list.insertItem(0, f"{operation} - {QDateTime.currentDateTime().toString()}")
        self.update_stats()

    def update_stats(self):
        total_images = self.db_table.rowCount()
        tagged_images = sum(1 for row in range(self.db_table.rowCount()) 
                          if self.db_table.item(row, 3).text().strip())
        recent_ops = self.operations_list.count()
        
        stats = f"""
        Total Images: {total_images}
        Tagged Images: {tagged_images}
        Recent Operations: {recent_ops}
        """
        self.stats_content.setText(stats)

    def open_config_dialog(self):
        dialog = ConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_config()
            self.load_config()
            self.status_bar.showMessage("Configuration saved and loaded.")
            self.log_operation("Configuration updated")

    def import_images(self):
        file_dialog = QFileDialog()
        current_filter = self.file_type_filter.currentText()
        file_paths, _ = file_dialog.getOpenFileNames(
            self, 
            "Select Images", 
            "", 
            current_filter
        )
        
        if file_paths:
            self.process_imported_files(file_paths)
            self.import_files_to_db(file_paths)

    def import_files_to_db(self, file_paths):
        progress = QProgressDialog("Importing images...", "Cancel", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, file_path in enumerate(file_paths):
            if progress.wasCanceled():
                break
                
            try:
                # Try to read the image to verify it's valid
                img = PILImage.open(file_path)
                img.verify()
                
                md5_checksum = self.compute_md5(file_path)
                image_info = self.db_manager.get_image_by_md5(md5_checksum)
                
                if not image_info:
                    # Extract metadata
                    metadata = {}
                    try:
                        img = PILImage.open(file_path)
                        if hasattr(img, '_getexif') and img._getexif():
                            exif = img._getexif()
                            metadata = {TAGS.get(tag_id, tag_id): str(value)
                                     for tag_id, value in exif.items()}
                    except:
                        pass
                    
                    reference_code = self.reference_service.generate_ordered_code()
                    self.db_manager.add_image(file_path, md5_checksum, reference_code, metadata)
                    imported_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                self.log_operation(f"Error importing {os.path.basename(file_path)}: {str(e)}")
            
            progress.setValue(i + 1)
        
        status_msg = (f"Imported {imported_count} new images "
                     f"(skipped {skipped_count}, errors {error_count})")
        self.status_bar.showMessage(status_msg)
        self.log_operation(status_msg)
        self.refresh_db_table()

    def export_database(self):
        file_dialog = QFileDialog()
        export_path, _ = file_dialog.getSaveFileName(
            self,
            "Export Database",
            "",
            "ZIP Archives (*.zip)"
        )
        
        if not export_path:
            return
            
        if not export_path.endswith('.zip'):
            export_path += '.zip'
            
        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Export database
                zipf.write(self.db_manager.db_path, 'photo_gallery.db')
                
                # Export configuration
                if os.path.exists(CONFIG_FILE):
                    zipf.write(CONFIG_FILE, 'config.json')
                
                # Export project folder if configured
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                        project_folder = config.get('project_folder')
                        if project_folder and os.path.exists(project_folder):
                            for root, _, files in os.walk(project_folder):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.join('project_files',
                                                         os.path.relpath(file_path, project_folder))
                                    zipf.write(file_path, arcname)
                except:
                    pass
                    
            self.status_bar.showMessage(f"Database exported to {export_path}")
            self.log_operation(f"Exported database to {export_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export database: {str(e)}")

    def compute_md5(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def apply_watermark_batch(self):
        checked_items = [self.import_list.item(i) for i in range(self.import_list.count()) if self.import_list.item(i).checkState() == Qt.CheckState.Checked]
        if not checked_items:
            self.status_bar.showMessage("No images selected for watermarking.")
            return

        opacity = self.opacity_slider.value() / 100.0
        success_count = 0
        fail_count = 0

        if self.text_watermark_radio.isChecked():
            watermark_text = self.watermark_text_input.text()
            if not watermark_text:
                self.status_bar.showMessage("Please enter watermark text.")
                return

            for item in checked_items:
                image_path = item.text()
                md5_checksum = self.compute_md5(image_path)
                image_record = self.db_manager.get_image_by_md5(md5_checksum)
                if not image_record:
                    fail_count += 1
                    continue
                reference_code = image_record["reference_code"]
                output_path = os.path.splitext(image_path)[0] + "_watermarked.jpg"
                try:
                    self.watermark_service.apply_text_watermark(
                        image_path,
                        output_path,
                        watermark_text,
                        opacity=opacity,
                        include_reference_code=reference_code
                    )
                    success_count += 1
                    self.log_operation(f"Applied text watermark to: {os.path.basename(image_path)}")
                except Exception as e:
                    fail_count += 1
                    self.log_operation(f"Failed to apply text watermark to: {os.path.basename(image_path)}")
        else:
            watermark_image_path = self.load_watermark_image_path()
            if not watermark_image_path:
                self.status_bar.showMessage("Please select a watermark image in configuration.")
                return

            # Load watermark position and scale from config
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    position_x = config.get("watermark_position_x", 0.9)
                    position_y = config.get("watermark_position_y", 0.9)
                    scale = config.get("watermark_scale", 0.1)
            except Exception:
                position_x, position_y, scale = 0.9, 0.9, 0.1

            for item in checked_items:
                image_path = item.text()
                md5_checksum = self.compute_md5(image_path)
                image_record = self.db_manager.get_image_by_md5(md5_checksum)
                if not image_record:
                    fail_count += 1
                    continue
                output_path = os.path.splitext(image_path)[0] + "_watermarked.jpg"
                try:
                    self.watermark_service.apply_image_watermark(
                        image_path,
                        output_path,
                        watermark_image_path,
                        position=(position_x, position_y),
                        scale=scale,
                        opacity=opacity
                    )
                    success_count += 1
                    self.log_operation(f"Applied image watermark to: {os.path.basename(image_path)}")
                except Exception as e:
                    fail_count += 1
                    self.log_operation(f"Failed to apply image watermark to: {os.path.basename(image_path)}")

        status_msg = f"Watermark applied to {success_count} images, failed on {fail_count}."
        self.status_bar.showMessage(status_msg)
        self.log_operation(status_msg)

    def load_watermark_image_path(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("watermark_image_path", "")
        except Exception:
            return ""

    def share_on_instagram(self):
        checked_items = [self.import_list.item(i) for i in range(self.import_list.count()) if self.import_list.item(i).checkState() == Qt.CheckState.Checked]
        if not checked_items:
            self.status_bar.showMessage("No images selected.")
            return
        caption = self.share_caption_input.toPlainText()
        if not caption:
            self.status_bar.showMessage("Please enter a caption.")
            return

        # For demo, assume image is accessible via URL or upload logic is handled externally
        # Here, we just simulate sharing by calling the service with a placeholder URL
        image_url = "https://example.com/path/to/image.jpg"  # Placeholder URL
        success = self.social_media_service.share_image(image_url, caption)
        
        if success:
            status_msg = "Image shared on Instagram successfully."
            self.status_bar.showMessage(status_msg)
            self.log_operation(f"Shared image on Instagram: {os.path.basename(checked_items[0].text())}")
        else:
            status_msg = "Failed to share image on Instagram."
            self.status_bar.showMessage(status_msg)
            self.log_operation(f"Failed to share image on Instagram: {os.path.basename(checked_items[0].text())}")

    def edit_tags(self):
        selected_rows = self.db_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("No image selected to edit tags.")
            return
        row = selected_rows[0].row()
        image_id = int(self.db_table.item(row, 0).text())
        current_tags = self.db_table.item(row, 3).text()

        text, ok = QInputDialog.getText(self, "Edit Tags", "Enter tags separated by commas:", QLineEdit.EchoMode.Normal, current_tags)
        if ok:
            tags = [tag.strip() for tag in text.split(",") if tag.strip()]
            self.db_manager.remove_tags_for_image(image_id)
            for tag in tags:
                tag_id = self.db_manager.add_tag(tag)
                self.db_manager.add_tag_to_image(image_id, tag_id)
            status_msg = f"Tags updated for image ID {image_id}."
            self.status_bar.showMessage(status_msg)
            self.log_operation(status_msg)
            self.refresh_db_table()

    def delete_image(self):
        selected_rows = self.db_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.showMessage("No image selected to delete.")
            return
        row = selected_rows[0].row()
        image_id = int(self.db_table.item(row, 0).text())
        file_path = self.db_table.item(row, 1).text()

        confirm = QMessageBox.question(self, "Delete Image", 
                                     f"Are you sure you want to delete image ID {image_id}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_image(image_id)
            status_msg = f"Image ID {image_id} deleted."
            self.status_bar.showMessage(status_msg)
            self.log_operation(status_msg)
            self.refresh_db_table()

    def open_scan_dialog(self):
        # Get all known MD5 checksums from the database
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT md5_checksum FROM images")
        known_checksums = [row['md5_checksum'] for row in cursor.fetchall()]

        dialog = ScanDriveDialog(self, known_checksums)
        dialog.exec()
        self.refresh_db_table()

    def verify_image_locations(self):
        progress = QProgressDialog("Verifying image locations...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        cursor = self.db_manager.conn.cursor()
        cursor.execute("""
            SELECT i.id, il.file_path 
            FROM images i 
            JOIN image_locations il ON i.id = il.image_id
        """)
        locations = cursor.fetchall()
        
        if not locations:
            self.status_bar.showMessage("No image locations to verify.")
            return
            
        total = len(locations)
        verified = 0
        removed = 0
        
        for i, (image_id, file_path) in enumerate(locations):
            if progress.wasCanceled():
                break
                
            if not os.path.exists(file_path):
                self.db_manager.verify_location(image_id, file_path, False)
                removed += 1
            else:
                self.db_manager.verify_location(image_id, file_path, True)
                verified += 1
                
            progress.setValue(int((i + 1) * 100 / total))
            
        self.status_bar.showMessage(
            f"Location verification complete. {verified} verified, {removed} removed.")
        self.log_operation(f"Verified image locations: {verified} valid, {removed} removed")
        self.refresh_db_table()

    def refresh_db_table(self):
        images = self.db_manager.get_all_images_with_tags()
        self.db_table.setRowCount(len(images))
        for row, (image, tags) in enumerate(images):
            self.db_table.setItem(row, 0, QTableWidgetItem(str(image['id'])))
            self.db_table.setItem(row, 1, QTableWidgetItem(
                image['project_path'] if image['project_path'] else 
                (image['locations'][0] if image['locations'] else "No location")
            ))
            self.db_table.setItem(row, 2, QTableWidgetItem(image['reference_code']))
            self.db_table.setItem(row, 3, QTableWidgetItem(
                ", ".join(tag['name'] for tag in tags) if tags else ""
            ))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
