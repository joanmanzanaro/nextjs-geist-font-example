import sys
import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QTabWidget, QLineEdit, QMessageBox, QStatusBar, QComboBox, QProgressDialog, QTreeWidget,
    QTreeWidgetItem, QInputDialog, QAbstractItemView, QScrollArea, QFormLayout, QSpinBox,
    QDoubleSpinBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont, QPixmap
from db_manager import DBManager, DBError
from reference_service import ReferenceService
from watermark_service import WatermarkService
from social_media_service import SocialMediaService
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

CONFIG_FILE = "config.json"

class SettingsDialog(QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config or {}

        self.layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.layout.addLayout(form_layout)

        # Watermark settings
        self.watermark_text_input = QLineEdit(self.config.get("watermark_text", "© My Photo Gallery"))
        form_layout.addRow("Watermark Text:", self.watermark_text_input)

        self.watermark_opacity_input = QDoubleSpinBox()
        self.watermark_opacity_input.setRange(0.0, 1.0)
        self.watermark_opacity_input.setSingleStep(0.1)
        self.watermark_opacity_input.setValue(self.config.get("watermark_opacity", 0.5))
        form_layout.addRow("Watermark Opacity:", self.watermark_opacity_input)

        self.watermark_font_size_input = QSpinBox()
        self.watermark_font_size_input.setRange(8, 72)
        self.watermark_font_size_input.setValue(self.config.get("watermark_font_size", 36))
        form_layout.addRow("Watermark Font Size:", self.watermark_font_size_input)

        # Social media API settings
        self.instagram_token_input = QLineEdit(self.config.get("instagram_token", ""))
        form_layout.addRow("Instagram Access Token:", self.instagram_token_input)

        self.instagram_account_id_input = QLineEdit(self.config.get("instagram_account_id", ""))
        form_layout.addRow("Instagram Account ID:", self.instagram_account_id_input)

        # Reference code settings
        self.reference_prefix_input = QLineEdit(self.config.get("reference_prefix", "REF"))
        form_layout.addRow("Reference Code Prefix:", self.reference_prefix_input)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def get_settings(self):
        return {
            "watermark_text": self.watermark_text_input.text(),
            "watermark_opacity": self.watermark_opacity_input.value(),
            "watermark_font_size": self.watermark_font_size_input.value(),
            "instagram_token": self.instagram_token_input.text(),
            "instagram_account_id": self.instagram_account_id_input.text(),
            "reference_prefix": self.reference_prefix_input.text(),
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery")
        self.setGeometry(100, 100, 1200, 800)

        # Load config
        self.config = self.load_config_file()

        # Initialize services with config
        try:
            self.db_manager = DBManager()
            self.reference_service = ReferenceService(prefix=self.config.get("reference_prefix", "REF"))
            self.watermark_service = WatermarkService()
            self.social_media_service = SocialMediaService(
                access_token=self.config.get("instagram_token", ""),
                instagram_account_id=self.config.get("instagram_account_id", "")
            )
        except DBError as e:
            QMessageBox.critical(self, "Database Error", str(e))
            sys.exit(1)

        # Initialize UI components
        self._setup_ui()

        # Load initial data
        self.refresh_db_table()
        self.update_stats()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Import Images Tab
        self.import_tab = QWidget()
        self._setup_import_tab()
        self.tabs.addTab(self.import_tab, "Import Images")

        # Image Database Tab
        self.database_tab = QWidget()
        self._setup_database_tab()
        self.tabs.addTab(self.database_tab, "Image Database")

        # View Images Tab
        self.view_tab = QWidget()
        self._setup_view_tab()
        self.tabs.addTab(self.view_tab, "View Images")

        # Overview Tab
        self.overview_tab = QWidget()
        self._setup_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        # Settings Tab
        self.settings_tab = QWidget()
        self._setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _setup_import_tab(self):
        layout = QVBoxLayout(self.import_tab)

        self.file_type_filter = QComboBox()
        self.file_type_filter.addItems([
            "All Images (*.png *.jpg *.jpeg *.bmp)",
            "PNG Files (*.png)",
            "JPEG Files (*.jpg *.jpeg)",
            "BMP Files (*.bmp)"
        ])
        layout.addWidget(self.file_type_filter)

        self.import_list = QListWidget()
        self.import_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.import_list)

        select_btn = QPushButton("Select Files to Import")
        select_btn.clicked.connect(self.select_files_to_import)
        layout.addWidget(select_btn)

        import_btn = QPushButton("Import Images")
        import_btn.clicked.connect(self.import_images)
        layout.addWidget(import_btn)

    def select_files_to_import(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(self.file_type_filter.currentText())
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            self.import_list.clear()
            self.import_list.addItems(files)

    def import_images(self):
        files = [self.import_list.item(i).text() for i in range(self.import_list.count())]
        if not files:
            QMessageBox.information(self, "No Files", "No files selected for import.")
            return

        progress = QProgressDialog("Importing images...", "Cancel", 0, len(files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        imported_count = 0
        for i, path in enumerate(files):
            if progress.wasCanceled():
                break
            try:
                md5 = self.compute_md5(path)
                if not self.db_manager.get_image_by_md5(md5):
                    ref_code = self.reference_service.generate_ordered_code()
                    self.db_manager.add_image(path, md5, ref_code)
                    imported_count += 1
            except Exception as e:
                self.status_bar.showMessage(f"Error importing {path}: {str(e)}")
            progress.setValue(i + 1)

        progress.close()
        self.status_bar.showMessage(f"Imported {imported_count} images.")
        self.import_list.clear()
        self.refresh_db_table()
        self.update_stats()

    def _setup_database_tab(self):
        layout = QVBoxLayout(self.database_tab)

        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["ID", "File Path", "Reference Code", "Tags"])
        self.db_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.db_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.db_table.cellClicked.connect(self.on_db_table_cell_clicked)
        layout.addWidget(self.db_table)

    def refresh_db_table(self):
        try:
            images_with_tags = self.db_manager.get_all_images_with_tags()
            self.db_table.setRowCount(len(images_with_tags))
            for row, (image, tags) in enumerate(images_with_tags):
                self.db_table.setItem(row, 0, QTableWidgetItem(str(image['id'])))
                file_path = image.get('project_path') or (image.get('locations') or [''])[0]
                self.db_table.setItem(row, 1, QTableWidgetItem(file_path))
                self.db_table.setItem(row, 2, QTableWidgetItem(image.get('reference_code', '')))
                tag_names = ", ".join(tag['name'] for tag in tags)
                self.db_table.setItem(row, 3, QTableWidgetItem(tag_names))
        except DBError as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def on_db_table_cell_clicked(self, row, column):
        image_id_item = self.db_table.item(row, 0)
        if not image_id_item:
            return
        image_id = int(image_id_item.text())
        self.load_image_details(image_id)

    def _setup_view_tab(self):
        layout = QVBoxLayout(self.view_tab)

        self.preview_label = QLabel("Select an image from the database tab to view details.")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)

        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        layout.addWidget(self.metadata_tree)

        tag_layout = QHBoxLayout()
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tag_layout.addWidget(self.tag_list)

        tag_buttons_layout = QVBoxLayout()
        add_tag_btn = QPushButton("Add Tag")
        add_tag_btn.clicked.connect(self.add_tag_to_selected_image)
        remove_tag_btn = QPushButton("Remove Selected Tag")
        remove_tag_btn.clicked.connect(self.remove_selected_tag)
        tag_buttons_layout.addWidget(add_tag_btn)
        tag_buttons_layout.addWidget(remove_tag_btn)
        tag_buttons_layout.addStretch()
        tag_layout.addLayout(tag_buttons_layout)

        layout.addLayout(tag_layout)

        self.current_view_image_id: Optional[int] = None

    def load_image_details(self, image_id: int):
        try:
            images_with_tags = self.db_manager.get_all_images_with_tags()
            image_data = next((img for img, _ in images_with_tags if img['id'] == image_id), None)
            tags = next((t for img, t in images_with_tags if img['id'] == image_id), [])
            if not image_data:
                return

            self.current_view_image_id = image_id

            # Load image preview
            file_path = image_data.get('project_path') or (image_data.get('locations') or [''])[0]
            if os.path.exists(file_path):
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("Image file not found.")

            # Load metadata
            self.metadata_tree.clear()
            try:
                with PILImage.open(file_path) as img:
                    info_item = QTreeWidgetItem(["Image Info"])
                    self.metadata_tree.addTopLevelItem(info_item)
                    info_item.addChild(QTreeWidgetItem(["Format", img.format]))
                    info_item.addChild(QTreeWidgetItem(["Size", f"{img.width} x {img.height}"]))
                    info_item.addChild(QTreeWidgetItem(["Mode", img.mode]))

                    exif = img._getexif()
                    if exif:
                        exif_item = QTreeWidgetItem(["EXIF Data"])
                        self.metadata_tree.addTopLevelItem(exif_item)
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, str(tag_id))
                            exif_item.addChild(QTreeWidgetItem([tag, str(value)]))
            except Exception:
                pass

            # Load tags
            self.tag_list.clear()
            for tag in tags:
                self.tag_list.addItem(tag['name'])

            self.tabs.setCurrentWidget(self.view_tab)
        except DBError as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def add_tag_to_selected_image(self):
        if self.current_view_image_id is None:
            QMessageBox.information(self, "No Image Selected", "Please select an image first.")
            return
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
        if ok and tag:
            try:
                tag_id = self.db_manager.add_tag(tag)
                self.db_manager.add_tag_to_image(self.current_view_image_id, tag_id)
                self.load_image_details(self.current_view_image_id)
                self.update_stats()
            except DBError as e:
                QMessageBox.warning(self, "Database Error", str(e))

    def remove_selected_tag(self):
        if self.current_view_image_id is None:
            QMessageBox.information(self, "No Image Selected", "Please select an image first.")
            return
        selected_items = self.tag_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Tag Selected", "Please select a tag to remove.")
            return
        tag_name = selected_items[0].text()
        try:
            tag_id = self.db_manager.get_tag_id_by_name(tag_name)
            if tag_id is None:
                QMessageBox.warning(self, "Tag Not Found", "Tag not found in database.")
                return
            self.db_manager.remove_tag_from_image(self.current_view_image_id, tag_id)
            self.load_image_details(self.current_view_image_id)
            self.update_stats()
        except DBError as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def _setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)

        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        self.operations_list = QListWidget()
        layout.addWidget(self.operations_list)

    def update_stats(self):
        try:
            total_images = self.db_table.rowCount()
            tagged_images = 0
            for row in range(total_images):
                tags_item = self.db_table.item(row, 3)
                if tags_item and tags_item.text().strip():
                    tagged_images += 1
            recent_ops = self.operations_list.count()

            stats_text = (
                f"Total Images: {total_images}\n"
                f"Tagged Images: {tagged_images}\n"
                f"Recent Operations: {recent_ops}"
            )
            self.stats_label.setText(stats_text)
        except Exception as e:
            self.status_bar.showMessage(f"Error updating stats: {str(e)}")

    def _setup_settings_tab(self):
        layout = QFormLayout(self.settings_tab)

        # Watermark settings
        self.watermark_text_input = QLineEdit(self.config.get("watermark_text", "© My Photo Gallery"))
        layout.addRow("Watermark Text:", self.watermark_text_input)

        self.watermark_opacity_input = QDoubleSpinBox()
        self.watermark_opacity_input.setRange(0.0, 1.0)
        self.watermark_opacity_input.setSingleStep(0.1)
        self.watermark_opacity_input.setValue(self.config.get("watermark_opacity", 0.5))
        layout.addRow("Watermark Opacity:", self.watermark_opacity_input)

        self.watermark_font_size_input = QSpinBox()
        self.watermark_font_size_input.setRange(8, 72)
        self.watermark_font_size_input.setValue(self.config.get("watermark_font_size", 36))
        layout.addRow("Watermark Font Size:", self.watermark_font_size_input)

        # Social media API settings
        self.instagram_token_input = QLineEdit(self.config.get("instagram_token", ""))
        layout.addRow("Instagram Access Token:", self.instagram_token_input)

        self.instagram_account_id_input = QLineEdit(self.config.get("instagram_account_id", ""))
        layout.addRow("Instagram Account ID:", self.instagram_account_id_input)

        # Reference code settings
        self.reference_prefix_input = QLineEdit(self.config.get("reference_prefix", "REF"))
        layout.addRow("Reference Code Prefix:", self.reference_prefix_input)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addRow(save_btn)

    def save_settings(self):
        self.config["watermark_text"] = self.watermark_text_input.text()
        self.config["watermark_opacity"] = self.watermark_opacity_input.value()
        self.config["watermark_font_size"] = self.watermark_font_size_input.value()
        self.config["instagram_token"] = self.instagram_token_input.text()
        self.config["instagram_account_id"] = self.instagram_account_id_input.text()
        self.config["reference_prefix"] = self.reference_prefix_input.text()

        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            # Update services with new settings
            self.reference_service.prefix = self.config["reference_prefix"]
            self.social_media_service.access_token = self.config["instagram_token"]
            self.social_media_service.instagram_account_id = self.config["instagram_account_id"]
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save settings: {str(e)}")

    def compute_md5(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def load_config_file(self) -> Dict[str, Any]:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def load_config(self):
        # This method is kept for backward compatibility, but config is loaded in __init__
        pass
