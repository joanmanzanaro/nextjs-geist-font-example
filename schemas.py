from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class ImageLocation:
    id: int
    file_path: str
    is_in_project_folder: bool
    last_verified: datetime

@dataclass
class Image:
    id: int
    md5_checksum: str
    reference_code: str
    imported_at: str
    project_path: Optional[str]  # Path in project folder if copied
    metadata: Dict  # Store EXIF and other metadata
    locations: List[ImageLocation]  # All known locations of this image

@dataclass
class Tag:
    id: int
    name: str

@dataclass
class ImageWithTags:
    image: Image
    tags: List[Tag]
