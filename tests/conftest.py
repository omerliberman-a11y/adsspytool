import os

# Set BEFORE adspy.config is imported so Pydantic Settings can load required fields.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5433/test_adspy"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("APIFY_TOKEN", "test-token")
