import os

import time, re
from .text_process import extract_url_tokens

from google.genai.types import GenerateContentConfig
from google import genai


class LLM:
    def __init__(self):
        self.api_keys = self._load_all_keys()
        self.current_key_idx = 0
        self._init_client()

    def _load_all_keys(self):
        keys = []
        if ", " in os.environ.get("GEMINI_API_KEY", ""):
            keys = os.environ.get("GEMINI_API_KEY", "").split(", ")
        return keys

    def _init_client(self):
        key = (
            self.api_keys[self.current_key_idx]
            if self.api_keys
            else os.getenv("GEMINI_API_KEY")
        )
        self.client = genai.Client(api_key=key)

    def _rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            self._init_client()
            return True
        return False

    # def generate_content(self, model, contents, max_retries=5, base_delay=22):
    def generate_content(self, model, contents, temperature=None, max_retries=5, base_delay=22):
        config = GenerateContentConfig(temperature=temperature) if temperature is not None else None
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=model, contents=contents, config=config
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "permission" in error_str.lower() or (
                    "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                ):
                    print(f"Rate limit hit on API Key #{self.current_key_idx + 1}...")

                    # try next key
                    if self._rotate_key():
                        print(
                            f"Swapped to API Key #{self.current_key_idx + 1}. Retrying instantly..."
                        )
                        continue

                    # If all keys are dead, fall back to sleeping
                    if attempt < max_retries - 1:
                        delay = base_delay
                        match = re.search(r"retry in (\d+\.?\d*)s", error_str)
                        if match:
                            delay = float(match.group(1)) + 1.0  # Add 1 second buffer

                        print(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {delay:.1f} seconds..."
                        )
                        time.sleep(delay)
                        base_delay += 10  # Fallback increase
                    else:
                        raise e
                else:
                    raise e

    def generate_news_summary(
        self, categories: list, title: str, description: str, url: str, date: str
    ) -> str:
        url_tokens = extract_url_tokens(url)

        prompt = f"""
        Please write a news summary based on the details below in less than 12 words.
        
        News Date - {date}
        
        Details -
        url keywords: {url_tokens}
        category: {categories}

        Primary Content -
        title: {title}
        description: {description}
        """
        response = self.generate_content("gemini-2.5-flash", prompt.strip(), temperature=0.5)
        return response.strip()


if __name__ == "__main__":
    import set_env
    import concurrent.futures

    set_env.set_cred_environments()
    llm = LLM()
    # Generate a response using a text prompt
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(2):
            future = executor.submit(
                llm.generate_content,
                "gemini-2.5-flash",
                "Explain the concept of quantum computing in one short sentence.",
            )
            print(f"Thread {i} started")
    print(future.result())
