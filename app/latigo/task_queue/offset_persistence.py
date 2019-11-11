from os import environ
from typing import Optional
import logging

from sqlalchemy import Column, String, Integer, DateTime
from latigo.db import session_scope, Base


logger = logging.getLogger(__name__)


class OffsetPersistanceInterface:
    def set(self, offset: str):
        pass

    def get(self, default: str = "@latest") -> Optional[str]:
        pass


class OffsetTable(Base):
    __tablename__ = "offset_checkpoints"
    name = Column(String(64), primary_key=True)
    offset = Column(String)
    created_at = Column(DateTime)

    def __init__(self, name: str, offset: str):
        self.name = name
        self.offset = offset


class DBOffsetPersistance(OffsetPersistanceInterface):
    def __init__(self, config: dict, name: str):
        self.config = config
        self.name = name

    def set(self, offset: str):
        with session_scope(self.config) as session:
            offset_entity = OffsetTable(self.name, offset)
            session.merge(offset_entity)

    def get(self, default: str = "@latest") -> Optional[str]:
        with session_scope(self.config) as session:
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
