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


def clear_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


@pytest.fixture(autouse=True)
def clean_test_state():
    from app.config import JOBS_DIR, STORAGE_DIR, UPLOADS_DIR
    from app.db import Base, engine

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    clear_dir(UPLOADS_DIR)
    clear_dir(JOBS_DIR)

    yield

    engine.dispose()
