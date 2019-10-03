from os import environ

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import Column, String, Integer, DateTime
from contextlib import contextmanager

connection_string = environ.get('LATIGO_INTERNAL_DATABASE', None)
print(f"CONNECTION STRING IS: {connection_string}")

engine = create_engine(connection_string, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class OffsetBookmark(Base):
    __tablename__ = 'offset_bookmarks'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    offset = Column(Integer)
    created_at = Column(DateTime)

    def __init__(self, name: str, offset: int):
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
    def set(self, offset: int): pass
    def get(self) -> int: pass


class DBOffsetPersistance(OffsetPersistanceInterface):
    def __init__(self, name: str):
        self.name = name

    def set(self, offset: int):
        with session_scope() as session:
            offset_entity = OffsetBookmark(self.name, offset)
            session.add(offset_entity)

    def get(self) -> int:
        with session_scope() as session:
            offset_entity = session.query(OffsetBookmark).filter_by(
                name=self.name).one_or_none()
            if offset_entity:
                return offset_entity.offset
        return None


class MemoryOffsetPersistance(OffsetPersistanceInterface):
    def __init__(self):
        self.offset = None

    def set(self, offset: int):
        self.offset = offset

    def get(self) -> str:
        return self.offset
