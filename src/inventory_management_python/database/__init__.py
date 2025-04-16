from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine = create_engine("sqlite:///local.db", echo=True)

from inventory_management_python.database.user import User  # noqa: E402, F401, F403

Base.metadata.create_all(engine)
