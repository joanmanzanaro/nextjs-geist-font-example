from dataclasses import dataclass

@dataclass
class ImageModel:
    id: int
    file_path: str
    md5_checksum: str
    reference_code: str
    imported_at: str
