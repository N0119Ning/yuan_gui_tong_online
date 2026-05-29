"""DeepSeek API client with retry logic."""

import os
import time
from openai import OpenAI


class LLMClient:
    def __init__(
        self,
        api_key: str = None,
        model: str = "deepseek-chat",
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.max_retries = max_retries
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )

    def chat(self, messages: list, temperature: float = 0.3) -> str:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"DeepSeek API 调用失败（重试 {self.max_retries} 次）: {last_error}")
