import os
import logging
from typing import Optional
from openai import AsyncOpenAI
from .base import LLM

class OpenAIModel(LLM):
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str]=None):
        api_key = os.getenv("OPENAI_API_KEY") if api_key is None or api_key == '' else api_key
        if api_key is None or api_key == '':
            logging.error('API key for OpenAI client not defined. Please set OPENAI_API_KEY environmental variable.')
            raise KeyError('API key for OpenAI client not defined. Please set OPENAI_API_KEY environmental variable.')
        self.client = AsyncOpenAI(api_key=api_key)
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