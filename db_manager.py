import sqlite3
from sqlite3 import Connection
from typing import List, Optional, Tuple, Any, Dict
import json
from datetime import datetime

class DBManager:
    def __init__(self, db_path: str = "photo_gallery.db"):
        self.db_path = db_path
        self.conn: Optional[Connection] = None
        self._connect()
        self._create_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Images table now stores core image info and project path
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            md5_checksum TEXT UNIQUE NOT NULL,
            reference_code TEXT UNIQUE NOT NULL,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            project_path TEXT,
            metadata TEXT
        )
        """)

        # New table for tracking all locations of each image
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            is_in_project_folder BOOLEAN NOT NULL,
            last_verified TIMESTAMP,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
            UNIQUE(image_id, file_path)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_tags (
            image_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (image_id, tag_id),
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """)
        
        self.conn.commit()

    def add_image(self, file_path: str, md5_checksum: str, reference_code: str, metadata: Dict = None) -> int:
        cursor = self.conn.cursor()
        
        # First, try to insert the image record
        cursor.execute("""
        INSERT INTO images (md5_checksum, reference_code, metadata)
        VALUES (?, ?, ?)
        """, (md5_checksum, reference_code, json.dumps(metadata or {})))
        
        image_id = cursor.lastrowid
        
        # Then add the initial file location
        cursor.execute("""
        INSERT INTO image_locations (image_id, file_path, is_in_project_folder, last_verified)
        VALUES (?, ?, ?, ?)
        """, (image_id, file_path, False, datetime.now().isoformat()))
        
        self.conn.commit()
        return image_id

    def get_image_by_md5(self, md5_checksum: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT i.*, GROUP_CONCAT(il.file_path) as locations
        FROM images i
        LEFT JOIN image_locations il ON i.id = il.image_id
        WHERE i.md5_checksum = ?
        GROUP BY i.id
        """, (md5_checksum,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['metadata'] = json.loads(result['metadata'])
            result['locations'] = result['locations'].split(',') if result['locations'] else []
            return result
        return None

    def add_image_location(self, image_id: int, file_path: str, is_in_project: bool = False):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO image_locations (image_id, file_path, is_in_project_folder, last_verified)
        VALUES (?, ?, ?, ?)
        """, (image_id, file_path, is_in_project, datetime.now().isoformat()))
        self.conn.commit()

    def update_image_metadata(self, image_id: int, metadata: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
        UPDATE images SET metadata = ? WHERE id = ?
        """, (json.dumps(metadata), image_id))
        self.conn.commit()

    def verify_location(self, image_id: int, file_path: str, exists: bool):
        cursor = self.conn.cursor()
        if exists:
            cursor.execute("""
            UPDATE image_locations 
            SET last_verified = ? 
            WHERE image_id = ? AND file_path = ?
            """, (datetime.now().isoformat(), image_id, file_path))
        else:
            cursor.execute("""
            DELETE FROM image_locations 
            WHERE image_id = ? AND file_path = ?
            """, (image_id, file_path))
        self.conn.commit()

    def set_project_path(self, image_id: int, project_path: str):
        cursor = self.conn.cursor()
        cursor.execute("""
        UPDATE images SET project_path = ? WHERE id = ?
        """, (project_path, image_id))
        self.conn.commit()

    def get_all_images_with_tags(self) -> List[Tuple[Any, List[Any]]]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT i.*, GROUP_CONCAT(t.name) as tag_names, GROUP_CONCAT(il.file_path) as locations
        FROM images i
        LEFT JOIN image_tags it ON i.id = it.image_id
        LEFT JOIN tags t ON it.tag_id = t.id
        LEFT JOIN image_locations il ON i.id = il.image_id
        GROUP BY i.id
        """)
        results = []
        for row in cursor.fetchall():
            image_dict = dict(row)
            image_dict['metadata'] = json.loads(image_dict['metadata'])
            image_dict['locations'] = image_dict['locations'].split(',') if image_dict['locations'] else []
            tags = [{'id': -1, 'name': tag} for tag in row['tag_names'].split(',')] if row['tag_names'] else []
            results.append((image_dict, tags))
        return results

    def add_tag(self, tag_name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
        self.conn.commit()
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        row = cursor.fetchone()
        return row["id"] if row else -1

    def add_tag_to_image(self, image_id: int, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO image_tags (image_id, tag_id)
        VALUES (?, ?)
        """, (image_id, tag_id))
        self.conn.commit()

    def remove_tags_for_image(self, image_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))
        self.conn.commit()

    def get_tags_for_image(self, image_id: int) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT t.name FROM tags t
        JOIN image_tags it ON t.id = it.tag_id
        WHERE it.image_id = ?
        """, (image_id,))
        return [row["name"] for row in cursor.fetchall()]

    def get_images_by_tag(self, tag_name: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT i.*, GROUP_CONCAT(il.file_path) as locations
        FROM images i
        JOIN image_tags it ON i.id = it.image_id
        JOIN tags t ON it.tag_id = t.id
        LEFT JOIN image_locations il ON i.id = il.image_id
        WHERE t.name = ?
        GROUP BY i.id
        """, (tag_name,))
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result['metadata'] = json.loads(result['metadata'])
            result['locations'] = result['locations'].split(',') if result['locations'] else []
            results.append(result)
        return results

    def delete_image(self, image_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
