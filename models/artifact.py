from dataclasses import dataclass

@dataclass
class Artifact:
    slide_number: int
    filename: str
    local_path: str
    sha256: str
    mime_type: str
    storage_path: str
    public_url: str
