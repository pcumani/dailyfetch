import os
import logging
from typing import Optional
from google import genai
from .base import LLM

class GoogleModel(LLM):

    def __init__(self, model: str = "gemini-2.5-flash", api_key: Optional[str]=None):
        api_key = os.getenv("GOOGLE_API_KEY") if api_key is None or api_key == '' else api_key
        if api_key is None or api_key == '':
            logging.error('API key for Google client not defined. Please set GOOGLE_API_KEY environmental variable.')
            raise KeyError('API key for Google client not defined. Please set GOOGLE_API_KEY environmental variable.')
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def summarize(self, text: str) -> str:
        response = await self.client.aio.models.generate_content(model=self.model, contents="Summarize the following news article. The result must be presented as a bullet point list in a markdown format. Here are the news:\n\n" + text)
        return response.text