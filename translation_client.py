"""
watsonx.ai Translation Client
Handles language detection and translation using watsonx.ai LLM.
"""

import os
import json
import requests
from typing import Optional
from dataclasses import dataclass
from token_manager import TokenManager


@dataclass
class TranslationResult:
    """Result from translation operation."""
    original_text: str
    translated_text: str
    source_language: str
    is_english: bool
    success: bool
    error_message: Optional[str] = None


class TranslationClient:
    """Client for watsonx.ai translation using LLM."""

    DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"

    TRANSLATION_PROMPT = '''You are a language detection and translation assistant.

TASK: Analyze the following text and respond in JSON format.

INPUT TEXT:
"""
{text}
"""

INSTRUCTIONS:
1. Detect the language of the input text
2. If the text is NOT in English, translate it to English
3. If the text IS in English, return it unchanged

RESPOND WITH ONLY THIS JSON FORMAT (no other text):
{{
    "source_language": "<detected language name>",
    "is_english": <true or false>,
    "translated_text": "<English translation or original if already English>"
}}

IMPORTANT:
- Return ONLY the JSON, no explanations
- Preserve the meaning and intent of the original text
- For mixed-language text, translate all non-English portions to English'''

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        model_id: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize the translation client.

        Args:
            api_key: IBM Cloud API key. Reads from IBM_API_KEY if not provided.
            project_id: watsonx.ai project ID. Reads from WATSONX_PROJECT_ID if not provided.
            model_id: LLM model to use. Defaults to mistral-small.
            base_url: watsonx.ai API URL. Defaults to us-south region.
        """
        self.api_key = api_key or os.getenv("IBM_API_KEY")
        self.project_id = project_id or os.getenv("WATSONX_PROJECT_ID")
        self.model_id = model_id or os.getenv(
            "WATSONX_MODEL_ID",
            "mistralai/mistral-small-3-1-24b-instruct-2503"
        )
        self.base_url = base_url or os.getenv("WATSONX_API_URL", self.DEFAULT_URL)

        if not self.api_key:
            raise ValueError("IBM API key required for translation")
        if not self.project_id:
            raise ValueError("watsonx.ai project ID required. Set WATSONX_PROJECT_ID env var.")

        self._token_manager = TokenManager(api_key=self.api_key)

    @property
    def endpoint(self) -> str:
        """Get the text generation endpoint."""
        return f"{self.base_url}/ml/v1/text/generation?version=2024-03-14"

    def detect_and_translate(self, text: str) -> TranslationResult:
        """
        Detect language and translate to English if needed.

        Args:
            text: Text to analyze and potentially translate.

        Returns:
            TranslationResult with translation details.
        """
        if not text or not text.strip():
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="unknown",
                is_english=True,
                success=True
            )

        prompt = self.TRANSLATION_PROMPT.format(text=text)

        payload = {
            "input": prompt,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 2000,
                "min_new_tokens": 10,
                "temperature": 0.1,
                "top_p": 1,
                "repetition_penalty": 1.0
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token_manager.get_token()}"
        }

        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                return self._parse_llm_response(response.json(), text)
            else:
                return TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language="unknown",
                    is_english=True,
                    success=False,
                    error_message=f"API Error {response.status_code}: {response.text[:200]}"
                )

        except requests.exceptions.Timeout:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="unknown",
                is_english=True,
                success=False,
                error_message="Translation request timed out"
            )
        except requests.exceptions.RequestException as e:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="unknown",
                is_english=True,
                success=False,
                error_message=f"Request failed: {str(e)}"
            )

    def _parse_llm_response(self, response: dict, original_text: str) -> TranslationResult:
        """Parse the LLM response into a TranslationResult."""
        try:
            # Extract generated text from watsonx.ai response structure
            results = response.get("results", [])
            if not results:
                raise ValueError("No results in response")

            generated_text = results[0].get("generated_text", "").strip()

            # Handle potential markdown code blocks
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0]
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0]

            # Clean up the text
            generated_text = generated_text.strip()

            data = json.loads(generated_text)

            return TranslationResult(
                original_text=original_text,
                translated_text=data.get("translated_text", original_text),
                source_language=data.get("source_language", "unknown"),
                is_english=data.get("is_english", True),
                success=True
            )

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # If parsing fails, assume English and return original
            return TranslationResult(
                original_text=original_text,
                translated_text=original_text,
                source_language="unknown",
                is_english=True,
                success=False,
                error_message=f"Failed to parse LLM response: {str(e)}"
            )


# Simple in-memory cache for repeated translations
_translation_cache = {}


def get_cached_translation(text: str, client: TranslationClient) -> TranslationResult:
    """Get translation with simple in-memory caching."""
    cache_key = hash(text)
    if cache_key not in _translation_cache:
        _translation_cache[cache_key] = client.detect_and_translate(text)
    return _translation_cache[cache_key]
