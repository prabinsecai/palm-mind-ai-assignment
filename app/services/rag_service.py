import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import get_settings
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore, SearchHit
from app.infrastructure.redis_memory import ChatMemory
from app.repositories.booking_repository import BookingRepository
from app.schemas.chat import BookingDetails, BookingDraft, BookingExtraction, Source

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatResult:
    answer: str
    sources: list[Source]
    booking: BookingDetails | None
    booking_id: UUID | None


class RAGService:
    def __init__(
        self,
        llm: OpenAIService,
        qdrant: QdrantStore,
        memory: ChatMemory,
        bookings: BookingRepository,
    ) -> None:
        self.llm = llm
        self.qdrant = qdrant
        self.memory = memory
        self.bookings = bookings

    async def chat(self, session_id: str, message: str) -> ChatResult:
        history = await self.memory.get(session_id)
        extraction = await self.llm.extract_booking(message, history, date.today())
        draft = await self.memory.get_booking_draft(session_id)

        if draft is not None or _has_booking_intent(extraction.intent):
            return await self._handle_booking(
                session_id,
                message,
                extraction,
                draft or BookingDraft(),
            )

        vector = (await self.llm.embed([message]))[0]
        hits = await self.qdrant.search(
            vector,
            limit=get_settings().rag_top_k,
        )
        logger.info("RAG retrieval completed: session_id=%s hits=%d", session_id, len(hits))
        context = "\n\n".join(_format_hit(hit) for hit in hits)
        answer = await self.llm.answer(message, context, history)
        await self.memory.append(
            session_id,
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        )
        sources = [
            Source(
                document_id=hit.document_id,
                filename=hit.filename,
                chunk_index=hit.chunk_index,
                score=hit.score,
            )
            for hit in hits
        ]
        return ChatResult(answer, sources, None, None)

    async def _handle_booking(
        self,
        session_id: str,
        message: str,
        extraction: BookingExtraction,
        draft: BookingDraft,
    ) -> ChatResult:
        values = draft.model_dump()
        invalid_fields: set[str] = set()
        for field in ("name", "email", "date", "time"):
            candidate = getattr(extraction, field)
            if candidate is not None:
                try:
                    values[field] = _validate_booking_field(field, candidate)
                except ValueError:
                    values[field] = None
                    invalid_fields.add(field)

        updated_draft = BookingDraft(**values)
        missing_fields = [
            field
            for field in ("name", "email", "date", "time")
            if getattr(updated_draft, field) is None
        ]
        if missing_fields:
            await self.memory.save_booking_draft(session_id, updated_draft)
            answer = _booking_follow_up(missing_fields, invalid_fields)
            await self._remember_turn(session_id, message, answer)
            return ChatResult(answer, [], None, None)

        try:
            details = BookingDetails(
                name=updated_draft.name or "",
                email=updated_draft.email or "",
                date=updated_draft.date or "",
                time=updated_draft.time or "",
            )
        except ValidationError as exc:
            raise ValueError("Booking draft failed final validation") from exc

        saved = await self.bookings.create(
            details.name,
            str(details.email),
            details.date,
            details.time,
        )
        await self.memory.clear_booking_draft(session_id)
        logger.info("Interview booking saved: booking_id=%s", saved.id)
        answer = (
            f"Thanks, {details.name}. Your interview is booked for {details.date} "
            f"at {details.time}. A confirmation can be sent to {details.email}."
        )
        await self._remember_turn(session_id, message, answer)
        return ChatResult(answer, [], details, saved.id)

    async def _remember_turn(
        self,
        session_id: str,
        message: str,
        answer: str,
    ) -> None:
        await self.memory.append(
            session_id,
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        )


def _has_booking_intent(intent: bool | str) -> bool:
    if isinstance(intent, bool):
        return intent
    return intent.strip().lower() == "true"


def _validate_booking_field(field: str, value: str) -> str:
    normalized = value.strip()
    if field == "name":
        if not normalized or len(normalized) > 200:
            raise ValueError("Candidate name is invalid")
        return normalized
    if field == "email":
        return str(TypeAdapter(EmailStr).validate_python(normalized))
    if field == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            raise ValueError("Date must use YYYY-MM-DD")
        parsed_date = date.fromisoformat(normalized)
        if parsed_date < date.today():
            raise ValueError("Interview date cannot be in the past")
        return normalized
    if field == "time":
        if not re.fullmatch(r"\d{2}:\d{2}", normalized):
            raise ValueError("Time must use HH:MM")
        datetime.strptime(normalized, "%H:%M")
        return normalized
    raise ValueError(f"Unknown booking field: {field}")


def _booking_follow_up(
    missing_fields: list[str],
    invalid_fields: set[str],
) -> str:
    labels = {
        "name": "full name",
        "email": "valid email address",
        "date": "date (YYYY-MM-DD)",
        "time": "time (HH:MM)",
    }
    prompts = [
        f"your {labels[field]} again" if field in invalid_fields else labels[field]
        for field in missing_fields
    ]
    if len(prompts) == 1:
        requested = prompts[0]
    else:
        requested = f"{', '.join(prompts[:-1])}, and {prompts[-1]}"
    return f"I can book the interview. Please provide {requested}."


def _format_hit(hit: SearchHit) -> str:
    return f"[{hit.filename}#{hit.chunk_index}]\n{hit.text}"
