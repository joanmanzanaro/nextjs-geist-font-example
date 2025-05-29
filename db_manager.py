import sqlite3
import json
from typing import List, Dict, Any, Tuple, Optional
from contextlib import contextmanager
from datetime import datetime

class DBError(Exception):
    """Base exception class for database errors."""
    pass

class DBManager:
    """Manager for handling database operations for the photo gallery."""
    
    def __init__(self, db_path: str = "photo_gallery.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()

    @contextmanager
    def _get_cursor(self):
        """
        Context manager for database connections.
        
        Yields:
            SQLite cursor object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DBError(f"Database operation failed: {str(e)}")
        finally:
            conn.close()

    def _initialize_db(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_cursor() as cursor:
            # Images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    md5_checksum TEXT UNIQUE,
                    reference_code TEXT,
                    project_path TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Image locations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER,
                    file_path TEXT,
                    is_verified BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
                )
            """)
            
            # Tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Image tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_tags (
                    image_id INTEGER,
                    tag_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (image_id, tag_id)
                )
            """)

    def add_image(self, file_path: str, md5_checksum: str, reference_code: str, 
                 metadata: Optional[Dict] = None) -> int:
        """
        Add a new image to the database.
        
        Args:
            file_path: Path to the image file
            md5_checksum: MD5 hash of the image
            reference_code: Unique reference code
            metadata: Optional metadata dictionary
            
        Returns:
            ID of the newly created image record
            
        Raises:
            DBError: If the operation fails
        """
        with self._get_cursor() as cursor:
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO images 
                (md5_checksum, reference_code, metadata, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (md5_checksum, reference_code, json.dumps(metadata or {}), now, now)
            )
            image_id = cursor.lastrowid
            
            cursor.execute(
                """
                INSERT INTO image_locations (image_id, file_path, created_at) 
                VALUES (?, ?, ?)
                """,
                (image_id, file_path, now)
            )
            
            return image_id

    def get_image_by_md5(self, md5_checksum: str) -> Optional[Dict[str, Any]]:
        """
        Get image information by MD5 checksum.
        
        Args:
            md5_checksum: MD5 hash of the image
            
        Returns:
            Dictionary containing image information or None if not found
        """
        with self._get_cursor() as cursor:
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

    def add_image_location(self, image_id: int, file_path: str, is_verified: bool = True) -> None:
        """
        Add a new location for an existing image.
        
        Args:
            image_id: ID of the image
            file_path: Path to the image file
            is_verified: Whether the location has been verified
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO image_locations (image_id, file_path, is_verified, created_at) 
                VALUES (?, ?, ?, ?)
                """,
                (image_id, file_path, is_verified, datetime.now().isoformat())
            )

    def verify_location(self, image_id: int, file_path: str, exists: bool) -> None:
        """
        Update or remove an image location based on verification.
        
        Args:
            image_id: ID of the image
            file_path: Path to verify
            exists: Whether the file exists at the location
        """
        with self._get_cursor() as cursor:
            if exists:
                cursor.execute(
                    """
                    UPDATE image_locations 
                    SET is_verified = 1 
                    WHERE image_id = ? AND file_path = ?
                    """,
                    (image_id, file_path)
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM image_locations 
                    WHERE image_id = ? AND file_path = ?
                    """,
                    (image_id, file_path)
                )

    def set_project_path(self, image_id: int, project_path: str) -> None:
        """
        Set the project path for an image.
        
        Args:
            image_id: ID of the image
            project_path: Path within the project
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE images 
                SET project_path = ?, updated_at = ? 
                WHERE id = ?
                """,
                (project_path, datetime.now().isoformat(), image_id)
            )

    def add_tag(self, tag_name: str) -> int:
        """
        Add a new tag or get existing tag ID.
        
        Args:
            tag_name: Name of the tag
            
        Returns:
            ID of the tag
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR IGNORE INTO tags (name, created_at) 
                VALUES (?, ?)
                """,
                (tag_name, datetime.now().isoformat())
            )
            
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            return cursor.fetchone()['id']

    def add_tag_to_image(self, image_id: int, tag_id: int) -> None:
        """
        Associate a tag with an image.
        
        Args:
            image_id: ID of the image
            tag_id: ID of the tag
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR IGNORE INTO image_tags (image_id, tag_id, created_at) 
                VALUES (?, ?, ?)
                """,
                (image_id, tag_id, datetime.now().isoformat())
            )

    def get_tags_for_image(self, image_id: int) -> List[str]:
        """
        Get all tags associated with an image.
        
        Args:
            image_id: ID of the image
            
        Returns:
            List of tag names
        """
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT t.name
                FROM tags t
                JOIN image_tags it ON t.id = it.tag_id
                WHERE it.image_id = ?
                ORDER BY t.name
            """, (image_id,))
            return [row['name'] for row in cursor.fetchall()]

    def remove_tags_for_image(self, image_id: int) -> None:
        """
        Remove all tags from an image.
        
        Args:
            image_id: ID of the image
        """
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))

    def update_image_metadata(self, image_id: int, metadata: Dict) -> None:
        """
        Update the metadata for an image.
        
        Args:
            image_id: ID of the image
            metadata: New metadata dictionary
        """
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE images 
                SET metadata = ?, updated_at = ? 
                WHERE id = ?
                """,
                (json.dumps(metadata), datetime.now().isoformat(), image_id)
            )

    def delete_image(self, image_id: int) -> None:
        """
        Delete an image and all associated data.
        
        Args:
            image_id: ID of the image to delete
        """
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))
            cursor.execute("DELETE FROM image_locations WHERE image_id = ?", (image_id,))
            cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))

    def get_all_images_with_tags(self) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Get all images with their associated tags.
        
        Returns:
            List of tuples containing (image_info, tags)
        """
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT i.*, GROUP_CONCAT(il.file_path) as locations,
                       GROUP_CONCAT(t.id) as tag_ids,
                       GROUP_CONCAT(t.name) as tag_names
                FROM images i
                LEFT JOIN image_locations il ON i.id = il.image_id
                LEFT JOIN image_tags it ON i.id = it.image_id
                LEFT JOIN tags t ON it.tag_id = t.id
                GROUP BY i.id
                ORDER BY i.created_at DESC
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

    def search_images(self, query: str, search_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Search for images based on various criteria.
        
        Args:
            query: Search query string
            search_type: Type of search ('all', 'filename', 'tags', 'metadata')
            
        Returns:
            List of matching image records
        """
        with self._get_cursor() as cursor:
            if search_type == 'all':
                cursor.execute("""
                    SELECT DISTINCT i.* FROM images i
                    LEFT JOIN image_locations il ON i.id = il.image_id
                    LEFT JOIN image_tags it ON i.id = it.image_id
                    LEFT JOIN tags t ON it.tag_id = t.id
                    WHERE il.file_path LIKE ? 
                    OR t.name LIKE ?
                    OR i.metadata LIKE ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            elif search_type == 'filename':
                cursor.execute("""
                    SELECT DISTINCT i.* FROM images i
                    JOIN image_locations il ON i.id = il.image_id
                    WHERE il.file_path LIKE ?
                """, (f"%{query}%",))
            elif search_type == 'tags':
                cursor.execute("""
                    SELECT DISTINCT i.* FROM images i
                    JOIN image_tags it ON i.id = it.image_id
                    JOIN tags t ON it.tag_id = t.id
                    WHERE t.name LIKE ?
                """, (f"%{query}%",))
            else:  # metadata
                cursor.execute("""
                    SELECT * FROM images
                    WHERE metadata LIKE ?
                """, (f"%{query}%",))
            
            return [dict(row) for row in cursor.fetchall()]
