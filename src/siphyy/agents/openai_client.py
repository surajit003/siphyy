"""OpenAI implementation of the `LLMClient` Protocol.

Uses the openai SDK's structured-output endpoint
(``client.beta.chat.completions.parse``) so agents receive a
Pydantic-validated object back, without prompt-format-and-extract
gymnastics.

This is one concrete implementation. Adding a different provider —
Anthropic, Gemini, a local Ollama or vLLM endpoint — is a new file
implementing the same single ``complete()`` method.

The ``openai`` package is imported lazily inside ``__init__`` so the
rest of ``siphyy`` works without the ``[llm]`` extras installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-2024-08-06"
"""The first gpt-4o snapshot with strict structured-output guarantees.
Override via the ``model`` parameter to use newer or cheaper models."""

DEFAULT_EMBED_MODEL = "text-embedding-3-small"
"""OpenAI's cheapest current embedding model — 1536 dims, $0.02 / 1M tokens.
Override via the ``embed_model`` parameter for higher-quality (text-embedding-3-large)
or legacy (text-embedding-ada-002) models."""


class OpenAILLMClient:
    """LLMClient backed by OpenAI's structured-output endpoint."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        """
        Args:
            model: OpenAI model identifier. Must support structured outputs.
            embed_model: OpenAI embedding model. Used by ``embed()``.
            api_key: API key. Falls back to ``OPENAI_API_KEY`` env var.
            base_url: For OpenAI-compatible endpoints — Ollama, vLLM,
                Together.ai, Groq, etc.
            client: Inject a pre-built ``openai.OpenAI`` instance. When
                provided, ``api_key`` and ``base_url`` are ignored.
        """
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._embed_model = embed_model

    def complete[T: BaseModel](
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        completion = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=response_model,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError(
                "OpenAI returned no parsed content. Refusal: "
                f"{completion.choices[0].message.refusal!r}"
            )
        return parsed

    def embed(self, text: str) -> list[float]:
        """Return an embedding for ``text`` via OpenAI's embeddings endpoint.

        Default model is ``text-embedding-3-small`` (1536 dims). Override at
        construction time with ``embed_model=`` for larger / legacy models.
        OpenAI-compatible endpoints (Ollama, vLLM) that don't ship an
        embeddings route will raise from the underlying client.
        """
        response = self._client.embeddings.create(
            model=self._embed_model,
            input=text,
        )
        return list(response.data[0].embedding)
