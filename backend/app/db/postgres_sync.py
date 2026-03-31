from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

sync_engine = create_engine(
    settings.database_url_sync,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

SyncSessionFactory = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


def get_sync_db() -> Session:
    return SyncSessionFactory()


# context manager that guarantees the session is closed after use
@contextmanager
def sync_db_session() -> Generator[Session, None, None]:
    db = SyncSessionFactory()
    try:
        yield db
    finally:
        db.close()
