from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

@dataclass
class ImageLocation:
    """
    Represents a physical location of an image file in the system.
    
    Attributes:
        id: Unique identifier for the location
        file_path: Absolute path to the image file
        is_in_project_folder: Whether the file is in the project's managed folder
        last_verified: Timestamp of last verification
        is_verified: Current verification status
        created_at: Timestamp when the location was added
    """
    id: int
    file_path: str
    is_in_project_folder: bool
    last_verified: datetime
    is_verified: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate location attributes after initialization."""
        if not isinstance(self.id, int):
            raise ValueError("Location ID must be an integer")
        
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("File path must be a non-empty string")

    def verify(self) -> bool:
        """
        Verify that the file exists at this location.
        
        Returns:
            True if file exists, False otherwise
        """
        exists = os.path.exists(self.file_path)
        self.is_verified = exists
        self.last_verified = datetime.now()
        return exists

    def to_dict(self) -> dict:
        """Convert the location to a dictionary."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'is_in_project_folder': self.is_in_project_folder,
            'last_verified': self.last_verified.isoformat(),
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ImageLocation':
        """Create a location from a dictionary."""
        return cls(
            id=data['id'],
            file_path=data['file_path'],
            is_in_project_folder=data['is_in_project_folder'],
            last_verified=datetime.fromisoformat(data['last_verified']),
            is_verified=data.get('is_verified', True),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )

@dataclass
class Image:
    """
    Represents an image in the system with its metadata and locations.
    
    Attributes:
        id: Unique identifier for the image
        md5_checksum: MD5 hash of the image file
        reference_code: Unique reference code
        imported_at: Timestamp when the image was imported
        project_path: Optional path within the project structure
        metadata: Dictionary containing image metadata
        locations: List of known locations for this image
        created_at: Timestamp when the image was created
        updated_at: Timestamp of last update
    """
    id: int
    md5_checksum: str
    reference_code: str
    imported_at: datetime
    project_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    locations: List[ImageLocation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate image attributes after initialization."""
        if not isinstance(self.id, int):
            raise ValueError("Image ID must be an integer")
        
        if not self.md5_checksum or not isinstance(self.md5_checksum, str):
            raise ValueError("MD5 checksum must be a non-empty string")
        
        if not self.reference_code or not isinstance(self.reference_code, str):
            raise ValueError("Reference code must be a non-empty string")

    def update_metadata(self, file_path: str) -> None:
        """
        Update metadata from the specified image file.
        
        Args:
            file_path: Path to the image file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            with PILImage.open(file_path) as img:
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
                            
                self.updated_at = datetime.now()
        except Exception as e:
            self.metadata['error'] = str(e)

    def add_location(self, location: ImageLocation) -> None:
        """Add a new location for this image."""
        if location not in self.locations:
            self.locations.append(location)
            self.updated_at = datetime.now()

    def remove_location(self, location: ImageLocation) -> None:
        """Remove a location from this image."""
        if location in self.locations:
            self.locations.remove(location)
            self.updated_at = datetime.now()

    def verify_locations(self) -> List[ImageLocation]:
        """
        Verify all locations of this image.
        
        Returns:
            List of valid locations
        """
        valid_locations = []
        for location in self.locations:
            if location.verify():
                valid_locations.append(location)
        return valid_locations

    def to_dict(self) -> dict:
        """Convert the image to a dictionary."""
        return {
            'id': self.id,
            'md5_checksum': self.md5_checksum,
            'reference_code': self.reference_code,
            'imported_at': self.imported_at.isoformat(),
            'project_path': self.project_path,
            'metadata': self.metadata,
            'locations': [loc.to_dict() for loc in self.locations],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Image':
        """Create an image from a dictionary."""
        return cls(
            id=data['id'],
            md5_checksum=data['md5_checksum'],
            reference_code=data['reference_code'],
            imported_at=datetime.fromisoformat(data['imported_at']),
            project_path=data.get('project_path'),
            metadata=data.get('metadata', {}),
            locations=[ImageLocation.from_dict(loc) for loc in data.get('locations', [])],
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )

@dataclass
class Tag:
    """
    Represents a tag that can be applied to images.
    
    Attributes:
        id: Unique identifier for the tag
        name: Name of the tag
        description: Optional description
        created_at: Timestamp when the tag was created
    """
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate tag attributes after initialization."""
        if not isinstance(self.id, int):
            raise ValueError("Tag ID must be an integer")
        
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Tag name must be a non-empty string")
        
        if len(self.name) > 50:
            raise ValueError("Tag name cannot exceed 50 characters")
        
        if self.description and len(self.description) > 200:
            raise ValueError("Tag description cannot exceed 200 characters")

    def to_dict(self) -> dict:
        """Convert the tag to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Tag':
        """Create a tag from a dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )

@dataclass
class ImageWithTags:
    """
    Represents an image with its associated tags.
    
    Attributes:
        image: The image object
        tags: List of associated tags
    """
    image: Image
    tags: List[Tag] = field(default_factory=list)

    def add_tag(self, tag: Tag) -> None:
        """Add a tag to the image."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: Tag) -> None:
        """Remove a tag from the image."""
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag_name: str) -> bool:
        """Check if the image has a tag with the given name."""
        return any(tag.name == tag_name for tag in self.tags)

    def to_dict(self) -> dict:
        """Convert the image with tags to a dictionary."""
        return {
            'image': self.image.to_dict(),
            'tags': [tag.to_dict() for tag in self.tags]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ImageWithTags':
        """Create an image with tags from a dictionary."""
        return cls(
            image=Image.from_dict(data['image']),
            tags=[Tag.from_dict(tag) for tag in data.get('tags', [])]
        )
