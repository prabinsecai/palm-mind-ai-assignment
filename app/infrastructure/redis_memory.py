import json
from redis.asyncio import Redis
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

class ChatMemory:
    def __init__(self) -> None:
        s=get_settings(); self.redis=Redis.from_url(s.redis_url, decode_responses=True); self.ttl=s.chat_memory_ttl_seconds
    def key(self, session_id: str) -> str: return f"palm-mind:chat:{session_id}"
    async def get(self, session_id: str) -> list[dict[str,str]]:
        try:
            raw=await self.redis.get(self.key(session_id)); return json.loads(raw) if raw else []
        except Exception as exc: raise ExternalServiceError("Redis memory read failed") from exc
    async def append(self, session_id: str, *messages: dict[str,str]) -> None:
        try:
            history=await self.get(session_id); history.extend(messages); history=history[-20:]
            await self.redis.set(self.key(session_id), json.dumps(history), ex=self.ttl)
        except Exception as exc: raise ExternalServiceError("Redis memory write failed") from exc
