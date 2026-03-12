"""
AI provider abstraction layer.

Supports OpenAI, Anthropic, and local models.
"""
import logging
from typing import Optional, List, NamedTuple

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not installed. Install with: pip install openai")

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic not installed. Install with: pip install anthropic")

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingResult(NamedTuple):
    """Result from embedding generation with usage stats."""
    embedding: List[float]
    input_tokens: int
    model: str


class GenerationResult(NamedTuple):
    """Result from LLM generation with usage stats."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class EmbeddingProvider:
    """
    Embedding generation provider.

    Supports:
    - OpenAI (text-embedding-3-small, text-embedding-3-large)
    - OpenAI (text-embedding-ada-002, legacy)
    - Local models (via sentence-transformers) - future
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize embedding provider.

        Args:
            provider: Provider name (openai, local). Defaults to settings.EMBEDDING_PROVIDER
            model: Model name. Defaults to settings.EMBEDDING_MODEL
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or settings.EMBEDDING_MODEL

        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise RuntimeError("OpenAI not installed. Install with: pip install openai")
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info(f"Initialized OpenAI embedding provider with model: {self.model}")
        elif self.provider == "local":
            raise NotImplementedError("Local embeddings not yet supported")
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text with usage tracking.

        Args:
            text: Text to embed (max 8192 tokens for text-embedding-3-small)

        Returns:
            EmbeddingResult with embedding vector and token usage

        Raises:
            ValueError: If text is empty
            RuntimeError: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if self.provider == "openai":
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                # OpenAI returns usage.total_tokens for embeddings
                input_tokens = response.usage.total_tokens if hasattr(response, 'usage') else self._estimate_tokens(text)

                return EmbeddingResult(
                    embedding=response.data[0].embedding,
                    input_tokens=input_tokens,
                    model=self.model
                )
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {e}")
                raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough estimation: 1 token ≈ 4 characters for English text."""
        return len(text) // 4

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> tuple[List[List[float]], int]:
        """
        Generate embeddings for multiple texts with total token usage.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)

        Returns:
            Tuple of (embeddings list, total_tokens_used)

        Raises:
            ValueError: If texts is empty
            RuntimeError: If API call fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        if self.provider == "openai":
            embeddings = []
            total_tokens = 0
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i+batch_size]
                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.model
                    )
                    embeddings.extend([item.embedding for item in response.data])
                    # Track token usage from batch
                    if hasattr(response, 'usage'):
                        total_tokens += response.usage.total_tokens
                    else:
                        # Estimate if not provided
                        total_tokens += sum(self._estimate_tokens(t) for t in batch)
                    logger.debug(f"Generated embeddings for batch {i//batch_size + 1} ({len(batch)} texts)")
                except Exception as e:
                    logger.error(f"OpenAI batch embedding generation failed for batch {i//batch_size + 1}: {e}")
                    raise RuntimeError(f"Failed to generate batch embeddings: {str(e)}")

            return embeddings, total_tokens


class LLMProvider:
    """
    Large Language Model provider.

    Supports:
    - OpenAI (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    - Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM provider.

        Args:
            provider: Provider name (openai, anthropic). Defaults to settings.LLM_PROVIDER
            model: Model name. Defaults to settings.LLM_MODEL
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL

        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise RuntimeError("OpenAI not installed. Install with: pip install openai")
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info(f"Initialized OpenAI LLM provider with model: {self.model}")
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise RuntimeError("Anthropic not installed. Install with: pip install anthropic")
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not configured in settings")
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info(f"Initialized Anthropic LLM provider with model: {self.model}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> GenerationResult:
        """
        Generate text completion with usage tracking.

        Args:
            prompt: User prompt
            system_message: System message for context
            temperature: Randomness (0-1). Lower = more deterministic
            max_tokens: Maximum response length

        Returns:
            GenerationResult with content and token usage

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If API call fails
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if self.provider == "openai":
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return GenerationResult(
                    content=response.choices[0].message.content,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    model=self.model
                )
            except Exception as e:
                logger.error(f"OpenAI generation failed: {e}")
                raise RuntimeError(f"Failed to generate text: {str(e)}")

        elif self.provider == "anthropic":
            try:
                response = self.client.messages.create(
                    model=self.model,
                    system=system_message or "",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return GenerationResult(
                    content=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=self.model
                )
            except Exception as e:
                logger.error(f"Anthropic generation failed: {e}")
                raise RuntimeError(f"Failed to generate text: {str(e)}")


# Global provider instances (can be configured via settings)
# These are lazily initialized to avoid errors when API keys are not configured
_embedding_provider: Optional[EmbeddingProvider] = None
_llm_provider: Optional[LLMProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    Get global embedding provider instance (singleton pattern).

    Returns:
        EmbeddingProvider instance

    Raises:
        ValueError: If provider configuration is invalid
    """
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider()
    return _embedding_provider


def get_llm_provider() -> LLMProvider:
    """
    Get global LLM provider instance (singleton pattern).

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider configuration is invalid
    """
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider


# For backward compatibility, expose as module-level variables
# But use functions to avoid initialization errors
embedding_provider = None  # Will be initialized on first use
llm_provider = None  # Will be initialized on first use
