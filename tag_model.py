from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class TagModel:
    """
    Model representing a tag in the photo gallery system.
    
    Attributes:
        id: Unique identifier for the tag
        name: Name of the tag
        created_at: Timestamp when the tag was created
        description: Optional description of the tag
        usage_count: Number of times the tag has been used
    """
    id: int
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    usage_count: int = 0

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
        
        if self.usage_count < 0:
            raise ValueError("Usage count cannot be negative")

    def increment_usage(self) -> None:
        """Increment the usage count of the tag."""
        self.usage_count += 1

    def decrement_usage(self) -> None:
        """Decrement the usage count of the tag."""
        if self.usage_count > 0:
            self.usage_count -= 1

    def to_dict(self) -> dict:
        """Convert the tag model to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'description': self.description,
            'usage_count': self.usage_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TagModel':
        """Create a tag model from a dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            description=data.get('description'),
            usage_count=data.get('usage_count', 0)
        )

    def __str__(self) -> str:
        """Return a string representation of the tag."""
        return f"{self.name} (used {self.usage_count} times)"
