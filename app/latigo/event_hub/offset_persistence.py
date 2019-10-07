from os import environ
from typing import Optional
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Column, String, Integer, DateTime
from contextlib import contextmanager

logger = logging.getLogger("latigo.offset_persistence")

connection_string = environ.get("LATIGO_INTERNAL_DATABASE", None)
logger.info(f"CONNECTION STRING IS: {connection_string}")

engine = create_engine(connection_string, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class OffsetTable(Base):
    __tablename__ = "offset_checkpoints"
    name = Column(String(64), primary_key=True)
    offset = Column(String)
    created_at = Column(DateTime)

    def __init__(self, name: str, offset: str):
        self.name = name
        self.offset = offset


Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


class OffsetPersistanceInterface:
    def set(self, offset: str):
        pass

    def get(self, default: str = "@latest") -> Optional[str]:
        pass


class DBOffsetPersistance(OffsetPersistanceInterface):
    def __init__(self, name: str):
        self.name = name

    def set(self, offset: str):
        with session_scope() as session:
            offset_entity = OffsetTable(self.name, offset)
            session.merge(offset_entity)

    def get(self, default: str = "@latest") -> Optional[str]:
        with session_scope() as session:
            offset_entity = session.query(OffsetTable).filter_by(name=self.name).one_or_none()
            if offset_entity:
                return offset_entity.offset
        return default


class MemoryOffsetPersistance(OffsetPersistanceInterface):
    def __init__(self):
        self.offset = None

    def set(self, offset: str):
        self.offset = offset

    def get(self, default: str = "@latest") -> Optional[str]:
        if not self.offset:
            return default
        return self.offset
