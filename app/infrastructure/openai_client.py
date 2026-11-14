import json
from collections.abc import Iterator
from datetime import date
from itertools import islice
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, LLMNotConfiguredError
from app.schemas.chat import BookingExtraction, ChatMessage


class OpenAIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.openai_api_key.strip():
            raise LLMNotConfiguredError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )

    def _require(self) -> AsyncOpenAI:
        return self.client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        try:
            for batch in _batches(texts, 64):
                response = await self._require().embeddings.create(
                    model=self.settings.openai_embedding_model,
                    input=batch,
                )
                ordered_data = sorted(response.data, key=lambda item: item.index)
                embeddings.extend(item.embedding for item in ordered_data)
            return embeddings
        except Exception as exc:
            raise ExternalServiceError("Embedding provider request failed") from exc

    async def answer(
        self,
        question: str,
        context: str,
        history: list[ChatMessage],
    ) -> str:
        system = (
            "You are Palm Mind's hiring assistant. Answer using only the supplied document "
            "context when factual. If the context does not contain the answer, say that the "
            "information is not available in the documents. Never invent interview slots or "
            "booking records. Keep answers concise and professional.\n\n"
            f"{context}"
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            *(cast(ChatCompletionMessageParam, item) for item in history),
            {"role": "user", "content": question},
        ]
        try:
            response = await self._require().chat.completions.create(
                model=self.settings.openai_chat_model,
                messages=messages,
                temperature=0.1,
            )
            return response.choices[0].message.content or "I could not generate an answer."
        except Exception as exc:
            raise ExternalServiceError("LLM request failed") from exc

    async def extract_booking(
        self,
        message: str,
        history: list[ChatMessage],
        today: date,
    ) -> BookingExtraction:
        system = (
            "You extract interview-booking intent and details. Use the full conversation history, "
            "set intent true only when the user clearly asks to book or schedule an interview, "
            "and extract only details the user provided. Interpret relative dates using today's "
            f"date, {today.isoformat()}, and return dates as YYYY-MM-DD. Return JSON with keys "
            "intent, name, email, date, and time. intent must be a JSON boolean. Use null for "
            "unknown fields. Do not invent values."
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            *(cast(ChatCompletionMessageParam, item) for item in history),
            {"role": "user", "content": message},
        ]
        try:
            response = await self._require().chat.completions.create(
                model=self.settings.openai_chat_model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            if not isinstance(payload, dict):
                raise ValueError("Booking extraction response must be a JSON object")
            payload["intent"] = _parse_intent(payload.get("intent"))
            return BookingExtraction.model_validate(payload)
        except Exception as exc:
            raise ExternalServiceError("Booking extraction failed") from exc


def _batches(values: list[str], batch_size: int) -> Iterator[list[str]]:
    iterator = iter(values)
    while batch := list(islice(iterator, batch_size)):
        yield batch


def _parse_intent(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return False
