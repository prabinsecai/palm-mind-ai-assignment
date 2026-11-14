from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.schemas.chat import BookingDraft, BookingExtraction, ChatMessage
from app.services.rag_service import RAGService


class FakeMemory:
    def __init__(self) -> None:
        self.history: list[ChatMessage] = []
        self.drafts: dict[str, BookingDraft] = {}

    async def get(self, session_id: str) -> list[ChatMessage]:
        return self.history.copy()

    async def append(self, session_id: str, *messages: ChatMessage) -> None:
        self.history.extend(messages)

    async def get_booking_draft(self, session_id: str) -> BookingDraft | None:
        draft = self.drafts.get(session_id)
        return draft.model_copy() if draft is not None else None

    async def save_booking_draft(
        self,
        session_id: str,
        draft: BookingDraft,
    ) -> None:
        self.drafts[session_id] = draft.model_copy()

    async def clear_booking_draft(self, session_id: str) -> None:
        self.drafts.pop(session_id, None)


class FakeLLM:
    def __init__(self, extractions: list[BookingExtraction]) -> None:
        self.extractions = extractions
        self.embed_calls = 0

    async def extract_booking(
        self,
        message: str,
        history: list[ChatMessage],
        today: date,
    ) -> BookingExtraction:
        return self.extractions.pop(0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        return [[0.1] for _ in texts]

    async def answer(
        self,
        question: str,
        context: str,
        history: list[ChatMessage],
    ) -> str:
        return "A document-grounded answer."


class FakeQdrant:
    async def search(self, vector: list[float], limit: int) -> list[object]:
        return []


class FakeBookings:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str, str]] = []

    async def create(self, name: str, email: str, date: str, time: str) -> object:
        self.created.append((name, email, date, time))
        return type("SavedBooking", (), {"id": uuid4()})()


def service_for(
    extractions: list[BookingExtraction],
) -> tuple[RAGService, FakeMemory, FakeBookings, FakeLLM]:
    memory = FakeMemory()
    bookings = FakeBookings()
    llm = FakeLLM(extractions)
    service = RAGService(llm, FakeQdrant(), memory, bookings)
    return service, memory, bookings, llm


@pytest.mark.asyncio
async def test_booking_collects_fields_over_multiple_turns() -> None:
    future_date = (date.today() + timedelta(days=3)).isoformat()
    service, memory, bookings, _ = service_for(
        [
            BookingExtraction(intent=True),
            BookingExtraction(
                intent=False,
                name="Jane Doe",
                email="jane@example.com",
            ),
            BookingExtraction(
                intent=False,
                date=future_date,
                time="10:30",
            ),
        ]
    )

    first = await service.chat("session-1", "I want to book an interview")
    assert "full name" in first.answer
    assert "valid email address" in first.answer
    assert "date (YYYY-MM-DD)" in first.answer
    assert "time (HH:MM)" in first.answer
    assert bookings.created == []

    second = await service.chat("session-1", "Jane Doe, jane@example.com")
    assert "date (YYYY-MM-DD)" in second.answer
    assert "time (HH:MM)" in second.answer
    assert "full name" not in second.answer
    assert "valid email address" not in second.answer
    assert bookings.created == []

    third = await service.chat("session-1", f"{future_date} at 10:30")
    assert third.booking is not None
    assert third.booking_id is not None
    assert third.booking.date == future_date
    assert len(bookings.created) == 1
    assert "session-1" not in memory.drafts


@pytest.mark.asyncio
async def test_invalid_email_and_past_date_are_reasked_without_saving() -> None:
    service, memory, bookings, _ = service_for(
        [
            BookingExtraction(
                intent=True,
                name="Jane Doe",
                email="not-an-email",
                date=(date.today() - timedelta(days=1)).isoformat(),
                time="10:30",
            )
        ]
    )

    result = await service.chat("session-invalid", "Book with these details")

    assert "valid email address again" in result.answer
    assert "date (YYYY-MM-DD) again" in result.answer
    assert "full name" not in result.answer
    assert "time (HH:MM)" not in result.answer
    assert bookings.created == []
    assert memory.drafts["session-invalid"].email is None
    assert memory.drafts["session-invalid"].date is None


@pytest.mark.asyncio
async def test_false_string_intent_does_not_trigger_booking() -> None:
    service, _, bookings, llm = service_for([BookingExtraction(intent="false")])

    result = await service.chat("session-false", "Tell me about the role")

    assert result.answer == "A document-grounded answer."
    assert result.booking is None
    assert bookings.created == []
    assert llm.embed_calls == 1
