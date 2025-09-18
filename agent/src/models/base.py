from abc import ABC, abstractmethod

class LLM(ABC):
    @abstractmethod
    async def summarize(self, text: str) -> str:
        pass