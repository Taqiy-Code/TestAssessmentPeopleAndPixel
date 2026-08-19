from pydantic import AliasChoices, BaseModel, Field, ConfigDict, model_validator
from typing import Any, Generic, TypeVar
from datetime import datetime
from fastapi import Query

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
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, default=10)
    q: str | None = None
    source: str | None = None
    from_date: datetime | None = Field(Query(default=None, alias="from"), validation_alias=AliasChoices("from", "from_date"))
    to: datetime | None = None 

    @model_validator(mode="after")
    def validate(self):       
        if self.from_date and self.to:
            if self.from_date > self.to:
                raise ValueError("from_date must be earlier than to_date")

        return self

class Pagination(BaseModel, Generic[T]):
    page: int = 1
    page_size: int = 10
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    data: list[T] 
