import os
import logging
from openai import AsyncOpenAI
from .base import LLM

class OpenAIModel(LLM):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def summarize(self, text: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a news summarizer."},
                {"role": "user", "content": text},
            ],
        )
        logging.info(response)
        return response.choices[0].message.content