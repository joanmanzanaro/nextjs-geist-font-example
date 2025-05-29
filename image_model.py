from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import os
from PIL import Image
from PIL.ExifTags import TAGS

@dataclass
class ImageModel:
    """
    Model representing an image in the photo gallery system.
    
    Attributes:
        id: Unique identifier for the image
        file_path: Path to the image file
        md5_checksum: MD5 hash of the image file
        reference_code: Unique reference code for the image
        imported_at: Timestamp when the image was imported
        metadata: Dictionary containing image metadata
        tags: List of associated tag IDs
        project_path: Optional path within the project structure
        last_accessed: Timestamp of last access
        file_size: Size of the image file in bytes
    """
    id: int
    file_path: str
    md5_checksum: str
    reference_code: str
    imported_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[int] = field(default_factory=list)
    project_path: Optional[str] = None
    last_accessed: Optional[datetime] = None
    file_size: Optional[int] = None

    def __post_init__(self):
        """Validate image attributes after initialization."""
        if not isinstance(self.id, int):
            raise ValueError("Image ID must be an integer")
        
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("File path must be a non-empty string")
        
        if not self.md5_checksum or not isinstance(self.md5_checksum, str):
            raise ValueError("MD5 checksum must be a non-empty string")
        
        if not self.reference_code or not isinstance(self.reference_code, str):
            raise ValueError("Reference code must be a non-empty string")
        
        # Update file size if file exists
        if os.path.exists(self.file_path):
            self.file_size = os.path.getsize(self.file_path)
            self.last_accessed = datetime.fromtimestamp(os.path.getatime(self.file_path))

    @classmethod
    def from_file(cls, file_path: str, id: int, reference_code: str) -> 'ImageModel':
        """
        Create an ImageModel instance from a file.
        
        Args:
            file_path: Path to the image file
            id: Unique identifier for the image
            reference_code: Reference code for the image
            
        Returns:
            New ImageModel instance
            
        Raises:
            ValueError: If file doesn't exist or isn't a valid image
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        # Calculate MD5 checksum
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        md5_checksum = hash_md5.hexdigest()

        # Extract metadata
        metadata = {}
        try:
            with Image.open(file_path) as img:
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                metadata['size'] = img.size
                
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id in exif:
                        try:
                            tag = TAGS.get(tag_id, tag_id)
                            metadata[tag] = str(exif[tag_id])
                        except:
                            continue
        except Exception as e:
            metadata['error'] = str(e)

        return cls(
            id=id,
            file_path=file_path,
            md5_checksum=md5_checksum,
            reference_code=reference_code,
            metadata=metadata
        )

    def verify_checksum(self) -> bool:
        """
        Verify that the file's current MD5 matches the stored checksum.
        
        Returns:
            True if checksums match, False otherwise
        """
        if not os.path.exists(self.file_path):
            return False

        hash_md5 = hashlib.md5()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest() == self.md5_checksum

    def update_metadata(self) -> None:
        """Update metadata from the current image file."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Image file not found: {self.file_path}")

        try:
            with Image.open(self.file_path) as img:
                self.metadata['format'] = img.format
                self.metadata['mode'] = img.mode
                self.metadata['size'] = img.size
                
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id in exif:
                        try:
                            tag = TAGS.get(tag_id, tag_id)
                            self.metadata[tag] = str(exif[tag_id])
                        except:
                            continue
        except Exception as e:
            self.metadata['error'] = str(e)

    def add_tag(self, tag_id: int) -> None:
        """Add a tag to the image."""
        if tag_id not in self.tags:
            self.tags.append(tag_id)

    def remove_tag(self, tag_id: int) -> None:
        """Remove a tag from the image."""
        if tag_id in self.tags:
            self.tags.remove(tag_id)

    def to_dict(self) -> dict:
        """Convert the image model to a dictionary."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'md5_checksum': self.md5_checksum,
            'reference_code': self.reference_code,
            'imported_at': self.imported_at.isoformat(),
            'metadata': self.metadata,
            'tags': self.tags,
            'project_path': self.project_path,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'file_size': self.file_size
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ImageModel':
        """Create an image model from a dictionary."""
        return cls(
            id=data['id'],
            file_path=data['file_path'],
            md5_checksum=data['md5_checksum'],
            reference_code=data['reference_code'],
            imported_at=datetime.fromisoformat(data['imported_at']),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            project_path=data.get('project_path'),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data.get('last_accessed') else None,
            file_size=data.get('file_size')
        )

    def __str__(self) -> str:
        """Return a string representation of the image."""
        return (f"Image {self.reference_code} "
                f"({os.path.basename(self.file_path)}, "
                f"{len(self.tags)} tags)")
