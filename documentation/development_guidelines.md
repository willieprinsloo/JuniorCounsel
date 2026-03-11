# Technical Guidelines

## Overview

This document defines best-practice technical architecture and API design standards for Python + Flask applications using PostgreSQL, SQLAlchemy, and Basic Authentication. It includes coding conventions, database integration, testing structure, and content API guidelines for search and pagination.

---

## 1. Core Stack

* **Language:** Python 3.9+
* **Framework:** Flask 3.0+
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy 2.0+
* **Auth:** Flask Basic Authentication (werkzeug.security)
* **Testing:** pytest
* **Environment:** `.env` managed via Pydantic `BaseSettings`

---

## 2. Project Layout

```
your-app/
├─ src/
│  ├─ app/
│  │  ├─ api/v1/          # REST Endpoints
│  │  ├─ auth/            # Authentication logic
│  │  ├─ core/            # Config, DB, Logging
│  │  ├─ persistence/     # Models and Repositories
│  │  └─ __init__.py
│  └─ wsgi.py
├─ tests/                 # Unit & Integration tests
├─ .env.example
├─ requirements.txt
└─ pytest.ini
```

---

## 3. Configuration & Environment

Use environment variables for all secrets and configurations.

**Example:**

```python
from pydantic import BaseSettings
class Settings(BaseSettings):
    ENV: str = "production"
    DEBUG: bool = False
    DATABASE_URL: str
    BASIC_AUTH_REALM: str = "App Admin"
    TEST_DATABASE_URL: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 4. Database Integration

**SQLAlchemy Engine Setup:**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = create_engine(settings.DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
```

**Schema Management:**

* Use `Base.metadata.create_all()` for dev/test.
* Manual SQL for schema changes in production.
* Add unique and indexed columns for optimized queries.

**Model Example:**

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
```

---

## 5. Authentication (Basic Auth)

**Key Guidelines:**

* Always use HTTPS.
* Store hashed passwords (bcrypt/argon2/werkzeug.security).
* Rate-limit login attempts.

**Example:**

```python
from werkzeug.security import check_password_hash

def require_basic_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth:
            abort(401, "Missing credentials")
        with session_scope() as s:
            user = UserRepository(s).get_by_username(auth.username)
            if not user or not check_password_hash(user.password_hash, auth.password):
                abort(401, "Invalid credentials")
        return view(*args, **kwargs)
    return wrapper
```

---

## 6. API Design

**Versioning:** `/api/v1/...`

**Response format:**

```json
{
  "data": [...],
  "page": 1,
  "per_page": 20,
  "total": 100,
  "next_page": 2
}
```

**Error responses:**

```json
{
  "error": "Invalid credentials",
  "code": 401
}
```

---

## 7. Content API — Search & Paging

### Design Principles

* Query parameters: `q`, `page`, `per_page`, `sort`, `order`
* Default `per_page=20`, max `100`
* Support case-insensitive substring search using `ILIKE`
* Provide pagination metadata and navigation

### Pydantic Query Schema

```python
class ListQuery(BaseModel):
    q: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    sort: Literal["created_at", "id"] = "created_at"
    order: Literal["asc", "desc"] = "desc"
```

### Repository Implementation

```python
class ArticleRepository:
    def list(self, q, page, per_page, sort, order):
        stmt = select(Article)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Article.title.ilike(like), Article.body.ilike(like)))

        direction = desc if order.lower() == "desc" else asc
        stmt = stmt.order_by(direction(getattr(Article, sort, Article.created_at)))

        total = self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        items = self.session.execute(stmt).scalars().all()
        return items, total or 0
```

### Endpoint Example

```python
@bp.get("/articles")
def list_articles():
    query = ListQuery(**request.args.to_dict())
    with session_scope() as s:
        repo = ArticleRepository(s)
        items, total = repo.list(query.q, query.page, query.per_page, query.sort, query.order)

    pages = ceil(total / query.per_page) if total else 0
    return jsonify({
        "items": [{"id": a.id, "title": a.title} for a in items],
        "page": query.page,
        "per_page": query.per_page,
        "total": total,
        "pages": pages,
        "next_page": query.page + 1 if query.page < pages else None,
        "prev_page": query.page - 1 if query.page > 1 else None
    })
```

---

## 8. Unit Testing

Use `pytest` with fixtures for DB and client isolation.

**tests/conftest.py**

```python
@pytest.fixture(scope="session")
def app():
    os.environ["ENV"] = "test"
    _app = create_app()
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    yield _app
    Base.metadata.drop_all(get_engine())

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db_session():
    with session_scope() as s:
        yield s
```

**Example test:**

```python
def test_article_pagination(db_session):
    for i in range(30):
        db_session.add(Article(title=f"Post {i}", body="sample text"))
    db_session.flush()

    repo = ArticleRepository(db_session)
    items, total = repo.list(None, 2, 10, "created_at", "desc")

    assert len(items) == 10
    assert total == 30
```

---

## 9. Indexing & Performance

**Recommended indexes:**

```sql
CREATE INDEX IF NOT EXISTS ix_articles_created_at_id ON articles (created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_articles_title_lower ON articles ((lower(title)));
```

---

## 10. Security Guidelines

* Use HTTPS for all traffic.
* Disable Flask debug in production.
* Rotate DB credentials.
* Sanitize and validate all query parameters.
* Limit maximum `per_page` to prevent load abuse.
* No plain-text passwords.

---

## 11. Deployment Notes

* Use systemd, gunicorn, or uwsgi to run `src/wsgi.py`.
* Keep `create_all()` limited to dev/test environments.
* Manually apply schema changes in production.

**Gunicorn Example:**

```bash
gunicorn -w 4 -b 0.0.0.0:8000 src.wsgi:app
```

---

## 12. Summary Checklist

| Area           | Best Practice                                  |
| -------------- | ---------------------------------------------- |
| Configuration  | Environment variables only                     |
| Authentication | Basic Auth (HTTPS, hashed passwords)           |
| Database       | SQLAlchemy ORM + manual schema control         |
| API            | Versioned `/api/v1`, consistent JSON responses |
| Content        | Search + Pagination with hard caps             |
| Testing        | pytest with isolated sessions                  |
| Security       | HTTPS, rate limits, parameter validation       |
| Performance    | Index sorting + search fields                  |

---

**End of Document**
