import logging
import typing

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from contextlib import contextmanager

logger = logging.getLogger("latigo.db")

Base = declarative_base()
db_is_set_up: bool = False
Session: typing.Optional[typing.Any]


def setup_db(config: dict) -> None:
    global db_is_set_up, Session
    if not db_is_set_up:
        db_is_set_up = True
        connection_string = config.get("db", {}).get("connection_string", None)
        if not connection_string:
            raise Exception("No connection string configured for database")
        logger.info(f"SETTING UP DATABASE WITH: {connection_string}")
        engine = create_engine(connection_string, echo=True)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)


@contextmanager
def session_scope(config: dict):
    """Provide a transactional scope around a series of operations."""
    setup_db(config)
    if not Session:
        raise Exception("No Session maker")
    session = Session()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
