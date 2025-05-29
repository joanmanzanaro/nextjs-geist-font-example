import uuid
from typing import Optional
from datetime import datetime

class ReferenceService:
    """Service for generating unique reference codes for images."""
    
    def __init__(self, prefix: str = "REF"):
        """
        Initialize the reference service.
        
        Args:
            prefix: Prefix to use for ordered codes (default: "REF")
        """
        self.counter = 0
        self.prefix = prefix
        self._last_reset = datetime.now().date()

    def generate_uuid(self) -> str:
        """
        Generate a UUID-based reference code.
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    def generate_ordered_code(self, date_prefix: Optional[str] = None) -> str:
        """
        Generate an ordered reference code with optional date prefix.
        
        Args:
            date_prefix: Optional date string to prefix the code
            
        Returns:
            Reference code string
        """
        # Reset counter if it's a new day
        current_date = datetime.now().date()
        if current_date != self._last_reset:
            self.counter = 0
            self._last_reset = current_date
        
        self.counter += 1
        
        if date_prefix:
            return f"{date_prefix}-{self.prefix}-{self.counter:06d}"
        return f"{self.prefix}-{self.counter:06d}"

    def generate_timestamp_code(self) -> str:
        """
        Generate a reference code based on current timestamp.
        
        Returns:
            Timestamp-based reference code
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{self.prefix}-{timestamp}"

    def parse_code(self, code: str) -> dict:
        """
        Parse a reference code to extract its components.
        
        Args:
            code: Reference code to parse
            
        Returns:
            Dictionary containing code components
        """
        parts = code.split('-')
        result = {
            'original': code,
            'type': 'unknown',
            'components': parts
        }
        
        if len(parts) == 2 and parts[0] == self.prefix:
            try:
                number = int(parts[1])
                result['type'] = 'ordered'
                result['number'] = number
            except ValueError:
                pass
                
        elif len(parts) == 3:
            try:
                datetime.strptime(parts[1], "%Y%m%d")
                result['type'] = 'timestamp'
                result['date'] = parts[1]
                result['time'] = parts[2]
            except ValueError:
                pass
                
        return result

    def validate_code(self, code: str) -> bool:
        """
        Validate if a given string matches the reference code format.
        
        Args:
            code: Reference code to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not code or not isinstance(code, str):
            return False
            
        parsed = self.parse_code(code)
        return parsed['type'] != 'unknown'

    def reset_counter(self) -> None:
        """Reset the ordered code counter."""
        self.counter = 0
        self._last_reset = datetime.now().date()
