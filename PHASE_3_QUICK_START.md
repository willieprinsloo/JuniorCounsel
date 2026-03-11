# Phase 3 - Quick Start Guide

**Ready to begin Phase 3 AI Integration?** Follow this guide to get started in 30 minutes.

---

## Prerequisites Check

Before starting, ensure Phase 2 is working:

```bash
# ✅ Check PostgreSQL is running
psql junior_counsel_dev -c "SELECT 1;"

# ✅ Check Redis is running
redis-cli ping
# Expected: PONG

# ✅ Check API server works
curl http://localhost:8000/health
# Expected: {"status":"ok","app_name":"Junior Counsel","environment":"development"}

# ✅ Check workers are running
ps aux | grep "run_workers.py"
# Expected: python run_workers.py running
```

If any check fails, review `NEXT_STEPS.md` for Phase 2 setup.

---

## Step 1: Install System Dependencies (5 minutes)

### macOS
```bash
# Install Tesseract OCR
brew install tesseract

# Install Poppler (for PDF to image conversion)
brew install poppler

# Verify installations
tesseract --version
pdftoppm -v
```

### Ubuntu/Debian
```bash
# Install Tesseract OCR
sudo apt update
sudo apt install tesseract-ocr

# Install Poppler
sudo apt install poppler-utils

# Verify installations
tesseract --version
pdftoppm -v
```

### Windows (WSL recommended)
```bash
# Use Ubuntu instructions in WSL
# Or install via Chocolatey:
choco install tesseract
choco install poppler
```

---

## Step 2: Update Python Dependencies (3 minutes)

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Add Phase 3 dependencies to requirements.txt
cat >> requirements.txt << 'EOF'

# Phase 3 - AI Integration
openai==1.12.0
anthropic==0.18.0

# OCR
pytesseract==0.3.10
pillow==10.2.0
pdf2image==1.17.0

# Text extraction
pypdf==4.0.0
python-docx==1.1.0
EOF

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure AI Provider API Keys (2 minutes)

### Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key (starts with `sk-...`)

### Get Anthropic API Key (Optional)
1. Go to https://console.anthropic.com/settings/keys
2. Create new API key
3. Copy key (starts with `sk-ant-...`)

### Update .env
```bash
# Add to .env file
cat >> .env << 'EOF'

# AI Providers (Phase 3)
OPENAI_API_KEY=sk-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Optional

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
EOF
```

### Update .env.example
```bash
# Add to .env.example for documentation
cat >> .env.example << 'EOF'

# AI Providers (Phase 3)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # Optional

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
EOF
```

---

## Step 4: Verify Setup (5 minutes)

### Test OpenAI Connection
```python
# Create test script: test_ai_setup.py
import os
from openai import OpenAI

# Test OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test embedding
response = client.embeddings.create(
    input="This is a test contract clause.",
    model="text-embedding-3-small"
)
embedding = response.data[0].embedding
print(f"✅ Embedding works: {len(embedding)} dimensions")

# Test LLM
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "Say 'API works!' if you can read this."}],
    max_tokens=50
)
print(f"✅ LLM works: {response.choices[0].message.content}")
```

```bash
# Run test
python test_ai_setup.py

# Expected output:
# ✅ Embedding works: 1536 dimensions
# ✅ LLM works: API works!
```

### Test Tesseract OCR
```python
# Create test script: test_ocr_setup.py
import pytesseract
from PIL import Image
import io

# Create simple test image
img = Image.new('RGB', (200, 50), color='white')
# In real test, use actual image with text

# Test OCR
text = pytesseract.image_to_string(img)
print(f"✅ Tesseract OCR is working")
```

---

## Step 5: Create pgvector Index (2 minutes)

```bash
# Connect to database
psql junior_counsel_dev

# Create HNSW index for fast vector search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

# Create additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(overall_status);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);

# Verify indexes
\d document_chunks

# Expected output includes:
# Indexes:
#     "document_chunks_embedding_idx" hnsw (embedding vector_cosine_ops)

\q
```

---

## Step 6: Start Phase 3.1 Implementation (Start coding!)

You're now ready to begin Phase 3.1 - AI Provider Setup.

### First File to Create

**File:** `src/app/core/ai_providers.py`

```python
"""
AI provider abstraction layer.

Supports OpenAI, Anthropic, and local models.
"""
import os
from typing import Optional, List
from openai import OpenAI
from anthropic import Anthropic

from app.core.config import settings


class EmbeddingProvider:
    """
    Embedding generation provider.

    Supports:
    - OpenAI (text-embedding-3-small, text-embedding-3-large)
    - Local models (via sentence-transformers) - future
    """

    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        self.provider = provider
        self.model = model

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif provider == "local":
            raise NotImplementedError("Local embeddings not yet supported")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (max 8192 tokens)

        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)
        """
        if self.provider == "openai":
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048)

        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                embeddings.extend([item.embedding for item in response.data])
            return embeddings


class LLMProvider:
    """
    Large Language Model provider.

    Supports:
    - OpenAI (gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    - Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
    """

    def __init__(self, provider: str = "openai", model: str = "gpt-4-turbo"):
        self.provider = provider
        self.model = model

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not configured")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system_message: System message for context
            temperature: Randomness (0-1)
            max_tokens: Maximum response length

        Returns:
            Generated text
        """
        if self.provider == "openai":
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                system=system_message or "",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text


# Global provider instances (configured from settings)
embedding_provider = EmbeddingProvider(
    provider=getattr(settings, 'EMBEDDING_PROVIDER', 'openai'),
    model=getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-3-small')
)

llm_provider = LLMProvider(
    provider=getattr(settings, 'LLM_PROVIDER', 'openai'),
    model=getattr(settings, 'LLM_MODEL', 'gpt-4-turbo')
)
```

### Test Your Implementation
```python
# Test in Python REPL
python

>>> from app.core.ai_providers import embedding_provider, llm_provider

# Test embedding
>>> embedding = embedding_provider.embed_text("Test contract clause")
>>> len(embedding)
1536
>>> print("✅ Embedding works")

# Test LLM
>>> response = llm_provider.generate("What is 2+2?")
>>> print(response)
"4" (or similar)
>>> print("✅ LLM works")
```

---

## Next Steps

### Follow the Implementation Checklist

Open `documentation/Phase_3_Implementation_Checklist.md` and follow day-by-day tasks.

**Recommended workflow:**
1. ✅ Day 1-2: Complete Phase 3.1 (AI providers) - **YOU ARE HERE**
2. Day 3-10: Phase 3.2 (Document processing)
3. Day 11-17: Phase 3.3 (Vector search & RAG)
4. Day 18-24: Phase 3.4 (Draft generation)
5. Day 25-28: Phase 3.5 (Testing & optimization)

### Daily Development Cycle
```bash
# Morning: Update config.py with new settings
nano src/app/core/config.py

# Create/update files according to checklist
nano src/app/workers/ocr.py

# Test your changes
pytest tests/unit/test_ocr.py -v

# Run full test suite periodically
pytest tests/ -v

# Commit progress daily
git add .
git commit -m "Phase 3.1: Implement AI providers"
git push
```

---

## Troubleshooting

### OpenAI API Key Invalid
```bash
# Verify API key format
echo $OPENAI_API_KEY | wc -c
# Should be ~51 characters starting with "sk-"

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
# Should return list of models
```

### Tesseract Not Found
```bash
# macOS: Check installation
which tesseract
# Expected: /opt/homebrew/bin/tesseract or /usr/local/bin/tesseract

# Ubuntu: Check installation
dpkg -l | grep tesseract
# Expected: ii  tesseract-ocr

# Test directly
tesseract --version
# Expected: tesseract 5.x.x
```

### pgvector Index Creation Fails
```bash
# Ensure pgvector extension is installed
psql junior_counsel_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# If not installed:
psql junior_counsel_dev -c "CREATE EXTENSION vector;"

# Then retry index creation
```

### Redis Connection Refused
```bash
# Check Redis status
redis-cli ping

# If fails, start Redis
brew services start redis  # macOS
sudo systemctl start redis  # Ubuntu

# Verify connection
redis-cli
> ping
PONG
> exit
```

---

## Reference Links

- **Phase 3 Plan:** `documentation/Phase_3_AI_Integration_Plan.md` (detailed technical plan)
- **Phase 3 Checklist:** `documentation/Phase_3_Implementation_Checklist.md` (day-by-day tasks)
- **Development Guidelines:** `documentation/development_guidelines.md` (coding standards)
- **Architecture:** `documentation/Architecture.md` (system design)
- **API Docs:** `documentation/API_Summary.md` (Phase 2 endpoints)

---

## Success Criteria

**You're ready to start Phase 3 when:**
- ✅ All Step 1-5 checks pass
- ✅ OpenAI API key works
- ✅ Tesseract OCR installed
- ✅ pgvector index created
- ✅ `ai_providers.py` file created and tested

**Phase 3 is complete when:**
- ✅ All 28 daily tasks in checklist are done
- ✅ Integration tests pass
- ✅ Performance targets met
- ✅ Documentation complete

---

**Good luck with Phase 3 implementation! 🚀**

For questions or issues, refer to:
- `CLAUDE.md` for project context
- `NEXT_STEPS.md` for Phase 2 status
- `documentation/Phase_3_Implementation_Checklist.md` for detailed tasks
