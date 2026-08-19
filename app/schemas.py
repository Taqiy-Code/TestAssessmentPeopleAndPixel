from pydantic import AliasChoices, BaseModel, Field, ConfigDict, model_validator
from typing import Any, Generic, TypeVar
from datetime import datetime
from fastapi import HTTPException, status, Query

T = TypeVar("T")

class MentionItem(BaseModel):
    external_id: str
    source: str
    title: str | None = None
    content: str
    url: str
    author: str | None = None
    published_at: Any = None
    engagement: Any = None

class MentionSearchFilter(BaseModel):
    page: int = 1
    page_size: int = 10
    q: str | None = None
    source: str | None = None
    from_date: datetime | None = Field(Query(default=None, alias="from"), validation_alias=AliasChoices("from", "from_date"))
    to: datetime | None = None 

    @model_validator(mode="after")
    def validate(self):
        if self.page < 1:
            raise HTTPException(detail="page must be greater than 0", status_code=status.HTTP_400_BAD_REQUEST)

        if self.page_size < 1:
            raise HTTPException(detail="page_size must be greater than 0", status_code=status.HTTP_400_BAD_REQUEST)
        
        if self.from_date and self.to:
            if self.from_date > self.to:
                raise HTTPException(detail="from_date must be earlier than to_date",status_code=status.HTTP_400_BAD_REQUEST)

        return self

class Pagination(BaseModel, Generic[T]):
    page: int = 1
    page_size: int = 10
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    data: list[T] 
