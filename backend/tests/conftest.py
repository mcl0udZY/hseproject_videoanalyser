import os
import shutil
from pathlib import Path

import pytest

TEST_STORAGE = Path("/tmp/videodigest-test-storage")

os.environ.setdefault("APP_NAME", "VideoDigest Test")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_STORAGE / 'test.db'}")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QUEUE_NAME", "test-video-jobs")
os.environ.setdefault("DEFAULT_ASR_MODEL", "tiny")
os.environ.setdefault("DEFAULT_LANGUAGE", "ru")
os.environ.setdefault("DEFAULT_SUMMARY_MODE", "extractive")

from app.config import JOBS_DIR, STORAGE_DIR, UPLOADS_DIR
from app.db import Base, engine


@pytest.fixture(autouse=True)
def clean_test_state():
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield
