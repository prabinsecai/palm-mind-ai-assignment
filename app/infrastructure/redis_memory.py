import json

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.schemas.chat import BookingDraft, ChatMessage


class ChatMemory:
    def __init__(self) -> None:
        settings = get_settings()
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.ttl = settings.chat_memory_ttl_seconds

    def key(self, session_id: str) -> str:
        return f"palm-mind:chat:{session_id}"

    def booking_key(self, session_id: str) -> str:
        return f"palm-mind:booking:{session_id}"

    async def get(self, session_id: str) -> list[ChatMessage]:
        try:
            raw = await self.redis.get(self.key(session_id))
            if raw is None:
                return []
            payload = json.loads(raw)
            if not isinstance(payload, list):
                raise ValueError("Conversation memory must be a JSON list")
            messages: list[ChatMessage] = []
            for item in payload:
                if (
                    not isinstance(item, dict)
                    or item.get("role") not in {"user", "assistant"}
                    or not isinstance(item.get("content"), str)
                ):
                    raise ValueError("Conversation memory contains an invalid message")
                messages.append({"role": item["role"], "content": item["content"]})
            return messages
        except Exception as exc:
            raise ExternalServiceError("Redis memory read failed") from exc

    async def append(self, session_id: str, *messages: ChatMessage) -> None:
        try:
            history = await self.get(session_id)
            history.extend(messages)
            await self.redis.set(
                self.key(session_id),
                json.dumps(history[-20:]),
                ex=self.ttl,
            )
        except Exception as exc:
            raise ExternalServiceError("Redis memory write failed") from exc

    async def get_booking_draft(self, session_id: str) -> BookingDraft | None:
        try:
            raw = await self.redis.get(self.booking_key(session_id))
            return BookingDraft.model_validate_json(raw) if raw is not None else None
        except Exception as exc:
            raise ExternalServiceError("Redis booking draft read failed") from exc

    async def save_booking_draft(
        self,
        session_id: str,
        draft: BookingDraft,
    ) -> None:
        try:
            await self.redis.set(
                self.booking_key(session_id),
                draft.model_dump_json(),
                ex=self.ttl,
            )
        except Exception as exc:
            raise ExternalServiceError("Redis booking draft write failed") from exc

    async def clear_booking_draft(self, session_id: str) -> None:
        try:
            await self.redis.delete(self.booking_key(session_id))
        except Exception as exc:
            raise ExternalServiceError("Redis booking draft deletion failed") from exc
