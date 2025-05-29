import uuid

class ReferenceService:
    def __init__(self):
        self.counter = 0

    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def generate_ordered_code(self) -> str:
        self.counter += 1
        return f"REF-{self.counter:06d}"
