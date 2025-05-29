import sqlite3
import json
from typing import List, Dict, Any, Tuple

class DBManager:
    def __init__(self, db_path: str = "photo_gallery.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_checksum TEXT UNIQUE,
                reference_code TEXT,
                project_path TEXT,
                metadata TEXT
            )
        """)
        
        # Image locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER,
                file_path TEXT,
                is_verified BOOLEAN DEFAULT 1,
                FOREIGN KEY (image_id) REFERENCES images(id)
            )
        """)
        
        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        """)
        
        # Image tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_tags (
                image_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (image_id) REFERENCES images(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (image_id, tag_id)
            )
        """)
        
        self.conn.commit()

    def add_image(self, file_path: str, md5_checksum: str, reference_code: str, metadata: Dict = None) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO images (md5_checksum, reference_code, metadata) VALUES (?, ?, ?)",
            (md5_checksum, reference_code, json.dumps(metadata or {}))
        )
        image_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO image_locations (image_id, file_path) VALUES (?, ?)",
            (image_id, file_path)
        )
        
        self.conn.commit()
        return image_id

    def get_image_by_md5(self, md5_checksum: str) -> Dict[str, Any]:
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

    def add_image_location(self, image_id: int, file_path: str, is_verified: bool = True):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO image_locations (image_id, file_path, is_verified) VALUES (?, ?, ?)",
            (image_id, file_path, is_verified)
        )
        self.conn.commit()

    def verify_location(self, image_id: int, file_path: str, exists: bool):
        cursor = self.conn.cursor()
        if exists:
            cursor.execute(
                "UPDATE image_locations SET is_verified = 1 WHERE image_id = ? AND file_path = ?",
                (image_id, file_path)
            )
        else:
            cursor.execute(
                "DELETE FROM image_locations WHERE image_id = ? AND file_path = ?",
                (image_id, file_path)
            )
        self.conn.commit()

    def set_project_path(self, image_id: int, project_path: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE images SET project_path = ? WHERE id = ?",
            (project_path, image_id)
        )
        self.conn.commit()

    def add_tag(self, tag_name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)",
            (tag_name,)
        )
        self.conn.commit()
        
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        return cursor.fetchone()['id']

    def add_tag_to_image(self, image_id: int, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO image_tags (image_id, tag_id) VALUES (?, ?)",
            (image_id, tag_id)
        )
        self.conn.commit()

    def get_tags_for_image(self, image_id: int) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.name
            FROM tags t
            JOIN image_tags it ON t.id = it.tag_id
            WHERE it.image_id = ?
        """, (image_id,))
        return [row['name'] for row in cursor.fetchall()]

    def remove_tags_for_image(self, image_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))
        self.conn.commit()

    def update_image_metadata(self, image_id: int, metadata: Dict):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE images SET metadata = ? WHERE id = ?",
            (json.dumps(metadata), image_id)
        )
        self.conn.commit()

    def delete_image(self, image_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))
        cursor.execute("DELETE FROM image_locations WHERE image_id = ?", (image_id,))
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        self.conn.commit()

    def get_all_images_with_tags(self) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT i.*, GROUP_CONCAT(il.file_path) as locations,
                   GROUP_CONCAT(t.id) as tag_ids,
                   GROUP_CONCAT(t.name) as tag_names
            FROM images i
            LEFT JOIN image_locations il ON i.id = il.image_id
            LEFT JOIN image_tags it ON i.id = it.image_id
            LEFT JOIN tags t ON it.tag_id = t.id
            GROUP BY i.id
        """)
        
        results = []
        for row in cursor.fetchall():
            image = dict(row)
            image['metadata'] = json.loads(image['metadata'])
            image['locations'] = image['locations'].split(',') if image['locations'] else []
            
            tags = []
            if row['tag_ids'] and row['tag_names']:
                tag_ids = row['tag_ids'].split(',')
                tag_names = row['tag_names'].split(',')
                tags = [{'id': int(tid), 'name': name} 
                       for tid, name in zip(tag_ids, tag_names)]
            
            results.append((image, tags))
        
        return results
