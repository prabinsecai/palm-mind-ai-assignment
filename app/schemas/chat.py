from typing import Literal, TypedDict
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=5000)


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class Source(BaseModel):
    document_id: UUID
    filename: str
    chunk_index: int
    score: float


class BookingDetails(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(pattern=r"^\d{2}:\d{2}$")


class BookingDraft(BaseModel):
    name: str | None = None
    email: str | None = None
    date: str | None = None
    time: str | None = None


class BookingExtraction(BaseModel):
    intent: bool | str = False
    name: str | None = None
    email: str | None = None
    date: str | None = None
    time: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source] = Field(default_factory=list)
    booking: BookingDetails | None = None
    booking_id: UUID | None = None
