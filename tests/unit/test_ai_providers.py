"""
Unit tests for AI provider abstraction layer.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.core.ai_providers import (
    EmbeddingProvider,
    LLMProvider,
    get_embedding_provider,
    get_llm_provider
)


class TestEmbeddingProvider:
    """Test EmbeddingProvider class."""

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_init_openai_success(self, mock_openai_class):
        """Test successful OpenAI provider initialization."""
        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                with patch('app.core.config.settings.EMBEDDING_MODEL', 'text-embedding-3-small'):
                    provider = EmbeddingProvider()

                    assert provider.provider == 'openai'
                    assert provider.model == 'text-embedding-3-small'
                    mock_openai_class.assert_called_once_with(api_key='sk-test-key')

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', False)
    def test_init_openai_not_installed(self):
        """Test initialization fails when OpenAI not installed."""
        with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
            with pytest.raises(RuntimeError, match="OpenAI not installed"):
                EmbeddingProvider()

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    def test_init_openai_no_api_key(self):
        """Test initialization fails when API key not configured."""
        with patch('app.core.config.settings.OPENAI_API_KEY', None):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                with pytest.raises(ValueError, match="OPENAI_API_KEY not configured"):
                    EmbeddingProvider()

    def test_init_unsupported_provider(self):
        """Test initialization fails for unsupported provider."""
        with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'invalid'):
            with pytest.raises(ValueError, match="Unsupported embedding provider"):
                EmbeddingProvider()

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_embed_text_success(self, mock_openai_class):
        """Test successful single text embedding."""
        # Setup mock response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dimensions
        mock_client.embeddings.create.return_value = mock_response

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                with patch('app.core.config.settings.EMBEDDING_MODEL', 'text-embedding-3-small'):
                    provider = EmbeddingProvider()
                    embedding = provider.embed_text("Test contract clause")

                    assert len(embedding) == 1536
                    assert embedding[0] == 0.1
                    mock_client.embeddings.create.assert_called_once()

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_embed_text_empty_string(self, mock_openai_class):
        """Test embed_text raises error for empty string."""
        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                provider = EmbeddingProvider()

                with pytest.raises(ValueError, match="Text cannot be empty"):
                    provider.embed_text("")

                with pytest.raises(ValueError, match="Text cannot be empty"):
                    provider.embed_text("   ")

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_embed_text_api_error(self, mock_openai_class):
        """Test embed_text handles API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.embeddings.create.side_effect = Exception("API rate limit")

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                provider = EmbeddingProvider()

                with pytest.raises(RuntimeError, match="Failed to generate embedding"):
                    provider.embed_text("Test text")

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_embed_batch_success(self, mock_openai_class):
        """Test successful batch embedding."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock response for batch
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_client.embeddings.create.return_value = mock_response

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                provider = EmbeddingProvider()
                texts = ["Text 1", "Text 2", "Text 3"]
                embeddings = provider.embed_batch(texts)

                assert len(embeddings) == 3
                assert len(embeddings[0]) == 1536
                assert embeddings[0][0] == 0.1
                assert embeddings[1][0] == 0.2

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_embed_batch_with_batching(self, mock_openai_class):
        """Test batch embedding with multiple API calls."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock response for each batch
        def create_response(batch_size):
            return Mock(data=[Mock(embedding=[0.1] * 1536) for _ in range(batch_size)])

        mock_client.embeddings.create.side_effect = [
            create_response(2),  # First batch of 2
            create_response(1)   # Second batch of 1
        ]

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.EMBEDDING_PROVIDER', 'openai'):
                provider = EmbeddingProvider()
                texts = ["Text 1", "Text 2", "Text 3"]
                embeddings = provider.embed_batch(texts, batch_size=2)

                assert len(embeddings) == 3
                assert mock_client.embeddings.create.call_count == 2


class TestLLMProvider:
    """Test LLMProvider class."""

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_init_openai_success(self, mock_openai_class):
        """Test successful OpenAI LLM initialization."""
        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'openai'):
                with patch('app.core.config.settings.LLM_MODEL', 'gpt-4-turbo'):
                    provider = LLMProvider()

                    assert provider.provider == 'openai'
                    assert provider.model == 'gpt-4-turbo'
                    mock_openai_class.assert_called_once_with(api_key='sk-test-key')

    @patch('app.core.ai_providers.ANTHROPIC_AVAILABLE', True)
    @patch('app.core.ai_providers.Anthropic')
    def test_init_anthropic_success(self, mock_anthropic_class):
        """Test successful Anthropic initialization."""
        with patch('app.core.config.settings.ANTHROPIC_API_KEY', 'sk-ant-test'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'anthropic'):
                with patch('app.core.config.settings.LLM_MODEL', 'claude-3-opus-20240229'):
                    provider = LLMProvider()

                    assert provider.provider == 'anthropic'
                    assert provider.model == 'claude-3-opus-20240229'
                    mock_anthropic_class.assert_called_once_with(api_key='sk-ant-test')

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_generate_openai_success(self, mock_openai_class):
        """Test successful text generation with OpenAI."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated response"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'openai'):
                provider = LLMProvider()
                result = provider.generate(
                    prompt="What is 2+2?",
                    system_message="You are a helpful assistant",
                    temperature=0.7,
                    max_tokens=100
                )

                assert result == "Generated response"
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args[1]
                assert call_args['temperature'] == 0.7
                assert call_args['max_tokens'] == 100

    @patch('app.core.ai_providers.ANTHROPIC_AVAILABLE', True)
    @patch('app.core.ai_providers.Anthropic')
    def test_generate_anthropic_success(self, mock_anthropic_class):
        """Test successful text generation with Anthropic."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response from Claude")]
        mock_client.messages.create.return_value = mock_response

        with patch('app.core.config.settings.ANTHROPIC_API_KEY', 'sk-ant-test'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'anthropic'):
                provider = LLMProvider()
                result = provider.generate(
                    prompt="What is 2+2?",
                    system_message="You are Claude",
                    temperature=0.5
                )

                assert result == "Generated response from Claude"
                mock_client.messages.create.assert_called_once()

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_generate_empty_prompt(self, mock_openai_class):
        """Test generate raises error for empty prompt."""
        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'openai'):
                provider = LLMProvider()

                with pytest.raises(ValueError, match="Prompt cannot be empty"):
                    provider.generate("")

                with pytest.raises(ValueError, match="Prompt cannot be empty"):
                    provider.generate("   ")

    @patch('app.core.ai_providers.OPENAI_AVAILABLE', True)
    @patch('app.core.ai_providers.OpenAI')
    def test_generate_api_error(self, mock_openai_class):
        """Test generate handles API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with patch('app.core.config.settings.OPENAI_API_KEY', 'sk-test-key'):
            with patch('app.core.config.settings.LLM_PROVIDER', 'openai'):
                provider = LLMProvider()

                with pytest.raises(RuntimeError, match="Failed to generate text"):
                    provider.generate("Test prompt")


class TestGlobalProviders:
    """Test global provider functions."""

    @patch('app.core.ai_providers._embedding_provider', None)
    @patch('app.core.ai_providers.EmbeddingProvider')
    def test_get_embedding_provider_singleton(self, mock_provider_class):
        """Test get_embedding_provider returns singleton."""
        mock_instance = Mock()
        mock_provider_class.return_value = mock_instance

        # Reset global variable
        import app.core.ai_providers as providers_module
        providers_module._embedding_provider = None

        provider1 = get_embedding_provider()
        provider2 = get_embedding_provider()

        assert provider1 is provider2
        mock_provider_class.assert_called_once()

    @patch('app.core.ai_providers._llm_provider', None)
    @patch('app.core.ai_providers.LLMProvider')
    def test_get_llm_provider_singleton(self, mock_provider_class):
        """Test get_llm_provider returns singleton."""
        mock_instance = Mock()
        mock_provider_class.return_value = mock_instance

        # Reset global variable
        import app.core.ai_providers as providers_module
        providers_module._llm_provider = None

        provider1 = get_llm_provider()
        provider2 = get_llm_provider()

        assert provider1 is provider2
        mock_provider_class.assert_called_once()
