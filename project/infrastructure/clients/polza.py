import asyncio

import httpx
from openai import AsyncOpenAI

from infrastructure.config.settings import Settings


class PolzaClientFactory:
    def __init__(self, settings: Settings) -> None:
        http_client = httpx.AsyncClient(timeout=60.0)
        self.client = AsyncOpenAI(
            base_url=settings.polza_base_url,
            api_key=settings.polza_api_key,
            http_client=http_client,
        )


class PolzaLLMClient:
    def __init__(self, settings: Settings) -> None:
        self.client = PolzaClientFactory(settings).client

    async def generate(self, content: str, model: str) -> str:
        completion = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
        )
        return completion.choices[0].message.content or ""


class PolzaEmbeddingClient:
    def __init__(self, settings: Settings, max_retries: int = 3, sleep_sec: float = 1.5) -> None:
        self.client = PolzaClientFactory(settings).client
        self.max_retries = max_retries
        self.sleep_sec = sleep_sec

    async def embed(self, text: str, model: str) -> list[float] | None:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.embeddings.create(model=model, input=text)
                if not response.data:
                    raise ValueError("No embedding data received")
                return response.data[0].embedding
            except Exception:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.sleep_sec)
        return None

    async def embed_batch(self, texts: list[str], model: str, batch_size: int = 64) -> list[list[float] | None]:
        vectors: list[list[float] | None] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await self.client.embeddings.create(model=model, input=batch)
                    if not response.data:
                        raise ValueError("No embedding data received")
                    vectors.extend([item.embedding for item in response.data])
                    break
                except Exception:
                    if attempt == self.max_retries:
                        vectors.extend([None] * len(batch))
                    else:
                        await asyncio.sleep(self.sleep_sec)

        return vectors
