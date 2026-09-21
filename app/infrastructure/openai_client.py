from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.exceptions import LLMNotConfiguredError, ExternalServiceError

class OpenAIService:
    def __init__(self) -> None:
        settings=get_settings()
        self.settings=settings
        self.client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

    def _require(self):
        if not self.client: raise LLMNotConfiguredError("OPENAI_API_KEY is not configured")
        return self.client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response=await self._require().embeddings.create(model=self.settings.openai_embedding_model, input=texts)
            return [x.embedding for x in response.data]
        except LLMNotConfiguredError: raise
        except Exception as exc: raise ExternalServiceError("Embedding provider request failed") from exc

    async def answer(self, question: str, context: str, history: list[dict[str,str]]) -> str:
        system=("You are Palm Mind's hiring assistant. Answer using only the supplied document context when factual. "
                 "If the context does not contain the answer, say that the information is not available in the documents. "
                 "Never invent interview slots or booking records. Keep answers concise and professional.\n\n" + context)
        messages=[{"role":"system","content":system}, *history, {"role":"user","content":question}]
        try:
            response=await self._require().chat.completions.create(model=self.settings.openai_chat_model, messages=messages, temperature=0.1)
            return response.choices[0].message.content or "I could not generate an answer."
        except LLMNotConfiguredError: raise
        except Exception as exc: raise ExternalServiceError("LLM request failed") from exc

    async def extract_booking(self, message: str, history: list[dict[str,str]]) -> dict | None:
        prompt=("Extract an interview booking only when the user is clearly requesting to book/schedule an interview. "
                "Return JSON with keys intent, name, email, date, time. intent must be true/false. "
                "Use null for missing fields. Do not invent values. Date format YYYY-MM-DD and time HH:MM.\n" + message)
        try:
            response=await self._require().chat.completions.create(
                model=self.settings.openai_chat_model,
                messages=[{"role":"system","content":"You are a strict structured information extractor."}, *history, {"role":"user","content":prompt}],
                temperature=0,
                response_format={"type":"json_object"},
            )
            import json
            return json.loads(response.choices[0].message.content or "{}")
        except LLMNotConfiguredError: raise
        except Exception as exc: raise ExternalServiceError("Booking extraction failed") from exc
