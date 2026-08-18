from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any

class MentionItem(BaseModel):
    external_id: str
    source: str
    title: Optional[str] = ""
    content: str
    url: str
    author: Optional[str] = None
    published_at: Optional[Any] = None
    engagement: Optional[Any] = None
    