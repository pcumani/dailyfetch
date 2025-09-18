import logging
from google import genai
from .base import LLM

class GoogleModel(LLM):

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.client = genai.Client()
        self.model = model

    async def summarize(self, text: str) -> str:
        response = await self.client.aio.models.generate_content(model="gemini-2.5-flash", contents="Summarize the following news article:\n" + text)
        return response.text