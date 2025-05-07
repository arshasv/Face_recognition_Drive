from pydantic import BaseModel
from typing import List

class ImageURL(BaseModel):
    name: str
    url: str

class ScanRequest(BaseModel):
    referenceImage: str
    imageUrls: List[ImageURL]