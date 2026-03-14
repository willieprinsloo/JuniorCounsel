"""
AI provider abstraction layer.

Supports OpenAI, Anthropic, and local models.
"""
import logging
from typing import Optional, List, NamedTuple
from uuid import UUID

try:
    from openai import OpenAI, RateLimitError as OpenAIRateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIRateLimitError = None
    logging.warning("OpenAI not installed. Install with: pip install openai")

try:
    from anthropic import Anthropic, RateLimitError as AnthropicRateLimitError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AnthropicRateLimitError = None
    logging.warning("Anthropic not installed. Install with: pip install anthropic")

from sqlalchemy.orm import Session
from app.core.config import settings
from app.persistence.models import TokenUsageTypeEnum

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

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        db: Optional[Session] = None,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        case_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize embedding provider.

        Args:
            provider: Provider name (openai, local, stub). Defaults to settings.EMBEDDING_PROVIDER
            model: Model name. Defaults to settings.EMBEDDING_MODEL
            db: Database session for token usage tracking (optional)
            organisation_id: Organisation ID for cost attribution (optional)
            user_id: User ID for cost attribution (optional)
            case_id: Case ID for cost attribution (optional)
            resource_type: Type of resource (document, draft_session, etc.) (optional)
            resource_id: ID of related resource (optional)
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or settings.EMBEDDING_MODEL
        self.db = db
        self.organisation_id = organisation_id
        self.user_id = user_id
        self.case_id = case_id
        self.resource_type = resource_type
        self.resource_id = resource_id

        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise RuntimeError("OpenAI not installed. Install with: pip install openai")
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self._rate_limit_error = OpenAIRateLimitError
            logger.info(f"Initialized OpenAI embedding provider with model: {self.model}")
        elif self.provider == "stub":
            # Stub provider for development/testing when API access is unavailable
            self.client = None
            self._rate_limit_error = None
            logger.warning(f"Initialized STUB embedding provider (development only) - returns fake embeddings")
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

        if self.provider == "stub":
            # Generate deterministic fake embeddings for development
            import hashlib
            import struct

            # Create a deterministic hash-based embedding
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()

            # Generate 1536 dimensions from hash (matching text-embedding-ada-002)
            embedding = []
            for i in range(1536):
                # Use hash bytes to generate deterministic floats between -1 and 1
                byte_idx = (i * 4) % len(hash_bytes)
                value = struct.unpack('f', hash_bytes[byte_idx:byte_idx+4] + b'\x00' * (4 - min(4, len(hash_bytes) - byte_idx)))[0]
                # Normalize to [-1, 1] range
                embedding.append(value % 2.0 - 1.0)

            input_tokens = self._estimate_tokens(text)
            logger.debug(f"Generated stub embedding for text ({input_tokens} tokens)")

            result = EmbeddingResult(
                embedding=embedding,
                input_tokens=input_tokens,
                model=self.model
            )

            # Record token usage if database session is available
            self._record_usage(result.input_tokens, 0)

            return result

        if self.provider == "openai":
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                # OpenAI returns usage.total_tokens for embeddings
                input_tokens = response.usage.total_tokens if hasattr(response, 'usage') else self._estimate_tokens(text)

                result = EmbeddingResult(
                    embedding=response.data[0].embedding,
                    input_tokens=input_tokens,
                    model=self.model
                )

                # Record token usage if database session is available
                self._record_usage(result.input_tokens, 0)

                return result
            except self._rate_limit_error as e:
                # Handle OpenAI quota/rate limit errors with user-friendly messages
                error_msg = str(e)
                if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                    logger.error(f"OpenAI quota exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API quota exceeded. Please check your OpenAI account "
                        "billing and plan details. For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
                else:
                    logger.error(f"OpenAI rate limit exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API rate limit exceeded. Please wait a moment and try again. "
                        "For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {e}")
                raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough estimation: 1 token ≈ 4 characters for English text."""
        return len(text) // 4

    def _record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """
        Record token usage to database if session is available.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (0 for embeddings)
        """
        if self.db is None:
            return

        try:
            from app.persistence.token_usage_repository import TokenUsageRepository

            token_repo = TokenUsageRepository(self.db)
            token_repo.record_usage(
                usage_type=TokenUsageTypeEnum.EMBEDDING,
                provider=self.provider,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                organisation_id=self.organisation_id,
                user_id=self.user_id,
                case_id=self.case_id,
                resource_type=self.resource_type,
                resource_id=self.resource_id,
            )
            logger.debug(f"Recorded embedding usage: {input_tokens} tokens (provider={self.provider}, model={self.model})")
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.warning(f"Failed to record token usage: {e}")

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

        if self.provider == "stub":
            # Generate stub embeddings for all texts
            embeddings = []
            total_tokens = 0
            for text in valid_texts:
                result = self.embed_text(text)
                embeddings.append(result.embedding)
                total_tokens += result.input_tokens

            logger.info(f"Generated {len(embeddings)} stub embeddings ({total_tokens} tokens)")

            # Record batch token usage
            self._record_usage(total_tokens, 0)

            return embeddings, total_tokens

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
                except self._rate_limit_error as e:
                    # Handle OpenAI quota/rate limit errors with user-friendly messages
                    error_msg = str(e)
                    if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                        logger.error(f"OpenAI quota exceeded: {error_msg}")
                        raise RuntimeError(
                            "OpenAI API quota exceeded. Please check your OpenAI account "
                            "billing and plan details. For more information, visit: "
                            "https://platform.openai.com/docs/guides/error-codes/api-errors"
                        ) from None
                    else:
                        logger.error(f"OpenAI rate limit exceeded: {error_msg}")
                        raise RuntimeError(
                            "OpenAI API rate limit exceeded. Please wait a moment and try again. "
                            "For more information, visit: "
                            "https://platform.openai.com/docs/guides/error-codes/api-errors"
                        ) from None
                except Exception as e:
                    logger.error(f"OpenAI batch embedding generation failed for batch {i//batch_size + 1}: {e}")
                    raise RuntimeError(f"Failed to generate batch embeddings: {str(e)}")

            # Record batch token usage
            self._record_usage(total_tokens, 0)

            return embeddings, total_tokens


class LLMProvider:
    """
    Large Language Model provider.

    Supports:
    - OpenAI (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    - Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        db: Optional[Session] = None,
        organisation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        case_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize LLM provider.

        Args:
            provider: Provider name (openai, anthropic). Defaults to settings.LLM_PROVIDER
            model: Model name. Defaults to settings.LLM_MODEL
            db: Database session for token usage tracking (optional)
            organisation_id: Organisation ID for cost attribution (optional)
            user_id: User ID for cost attribution (optional)
            case_id: Case ID for cost attribution (optional)
            resource_type: Type of resource (document, draft_session, etc.) (optional)
            resource_id: ID of related resource (optional)
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.db = db
        self.organisation_id = organisation_id
        self.user_id = user_id
        self.case_id = case_id
        self.resource_type = resource_type
        self.resource_id = resource_id

        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise RuntimeError("OpenAI not installed. Install with: pip install openai")
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self._rate_limit_error = OpenAIRateLimitError
            logger.info(f"Initialized OpenAI LLM provider with model: {self.model}")
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise RuntimeError("Anthropic not installed. Install with: pip install anthropic")
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not configured in settings")
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self._rate_limit_error = AnthropicRateLimitError
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
                # GPT-5 and newer models use max_completion_tokens instead of max_tokens
                # and only support temperature=1
                if self.model.startswith("gpt-5") or self.model.startswith("o1") or self.model.startswith("o3") or self.model.startswith("o4"):
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=1,  # GPT-5/o-series only support temperature=1
                        max_completion_tokens=max_tokens
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                result = GenerationResult(
                    content=response.choices[0].message.content,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    model=self.model
                )

                # Record token usage if database session is available
                self._record_usage(result.input_tokens, result.output_tokens)

                return result
            except self._rate_limit_error as e:
                # Handle OpenAI quota/rate limit errors with user-friendly messages
                error_msg = str(e)
                if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                    logger.error(f"OpenAI quota exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API quota exceeded. Please check your OpenAI account "
                        "billing and plan details. For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
                else:
                    logger.error(f"OpenAI rate limit exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API rate limit exceeded. Please wait a moment and try again. "
                        "For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
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
                result = GenerationResult(
                    content=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=self.model
                )

                # Record token usage if database session is available
                self._record_usage(result.input_tokens, result.output_tokens)

                return result
            except self._rate_limit_error as e:
                # Handle Anthropic quota/rate limit errors with user-friendly messages
                error_msg = str(e)
                if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                    logger.error(f"Anthropic quota exceeded: {error_msg}")
                    raise RuntimeError(
                        "Anthropic API quota exceeded. Please check your Anthropic account "
                        "billing and plan details. For more information, visit: "
                        "https://docs.anthropic.com/en/api/errors"
                    ) from None
                else:
                    logger.error(f"Anthropic rate limit exceeded: {error_msg}")
                    raise RuntimeError(
                        "Anthropic API rate limit exceeded. Please wait a moment and try again. "
                        "For more information, visit: "
                        "https://docs.anthropic.com/en/api/errors"
                    ) from None
            except Exception as e:
                logger.error(f"Anthropic generation failed: {e}")
                raise RuntimeError(f"Failed to generate text: {str(e)}")

    def _record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """
        Record token usage to database if session is available.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        if self.db is None:
            return

        try:
            from app.persistence.token_usage_repository import TokenUsageRepository

            token_repo = TokenUsageRepository(self.db)
            token_repo.record_usage(
                usage_type=TokenUsageTypeEnum.LLM_GENERATION,
                provider=self.provider,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                organisation_id=self.organisation_id,
                user_id=self.user_id,
                case_id=self.case_id,
                resource_type=self.resource_type,
                resource_id=self.resource_id,
            )
            logger.debug(
                f"Recorded LLM usage: {input_tokens} input + {output_tokens} output tokens "
                f"(provider={self.provider}, model={self.model})"
            )
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.warning(f"Failed to record token usage: {e}")

    def generate_with_tools(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 8000
    ) -> tuple[str, Optional[List[dict]], int, int]:
        """
        Generate text completion with tool calling support.

        Args:
            messages: List of message dicts with role and content
            tools: List of tool definitions (OpenAI function calling format)
            tool_choice: "auto", "none", or specific tool name
            temperature: Randomness (0-1). Lower = more deterministic
            max_tokens: Maximum response length

        Returns:
            Tuple of (content, tool_calls, input_tokens, output_tokens)
            tool_calls is None if no tools were called

        Raises:
            ValueError: If messages is empty
            RuntimeError: If API call fails
        """
        if not messages:
            raise ValueError("Messages cannot be empty")

        if self.provider == "openai":
            try:
                # GPT-5 and newer models use max_completion_tokens instead of max_tokens
                # and only support temperature=1
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                }

                if self.model.startswith("gpt-5") or self.model.startswith("o1") or self.model.startswith("o3") or self.model.startswith("o4"):
                    kwargs["temperature"] = 1  # GPT-5/o-series only support temperature=1
                    kwargs["max_completion_tokens"] = max_tokens
                else:
                    kwargs["temperature"] = temperature
                    kwargs["max_tokens"] = max_tokens

                # Add tools if provided
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice

                response = self.client.chat.completions.create(**kwargs)

                message = response.choices[0].message
                content = message.content or ""
                tool_calls = None

                # Extract tool calls if present
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    tool_calls = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]

                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                # Record token usage if database session is available
                self._record_usage(input_tokens, output_tokens)

                return content, tool_calls, input_tokens, output_tokens

            except self._rate_limit_error as e:
                # Handle OpenAI quota/rate limit errors with user-friendly messages
                error_msg = str(e)
                if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                    logger.error(f"OpenAI quota exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API quota exceeded. Please check your OpenAI account "
                        "billing and plan details. For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
                else:
                    logger.error(f"OpenAI rate limit exceeded: {error_msg}")
                    raise RuntimeError(
                        "OpenAI API rate limit exceeded. Please wait a moment and try again. "
                        "For more information, visit: "
                        "https://platform.openai.com/docs/guides/error-codes/api-errors"
                    ) from None
            except Exception as e:
                logger.error(f"OpenAI generation with tools failed: {e}")
                raise RuntimeError(f"Failed to generate text: {str(e)}")

        elif self.provider == "anthropic":
            # Anthropic doesn't support tool calling in the same way
            # For now, just use regular generation
            logger.warning("Tool calling not fully supported for Anthropic, using regular generation")
            result = self.generate(
                prompt=messages[-1]["content"] if messages else "",
                system_message=messages[0]["content"] if messages and messages[0]["role"] == "system" else None,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return result.content, None, result.input_tokens, result.output_tokens


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
