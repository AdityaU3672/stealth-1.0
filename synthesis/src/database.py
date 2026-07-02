from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    pass


def build_asyncpg_url_and_connect_args(database_url: str) -> tuple[str, dict]:
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    connect_args: dict = {}

    sslmode = query.pop("sslmode", None)
    if sslmode:
        # asyncpg expects "ssl", not libpq's "sslmode".
        if sslmode in {"require", "verify-ca", "verify-full"}:
            connect_args["ssl"] = "require"
        elif sslmode == "disable":
            connect_args["ssl"] = False

    # Not supported by asyncpg as a DSN option.
    query.pop("channel_binding", None)

    normalized = url.set(query=query).render_as_string(hide_password=False)
    return normalized, connect_args


ASYNC_DATABASE_URL, ASYNC_CONNECT_ARGS = build_asyncpg_url_and_connect_args(settings.DATABASE_URL)


engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args=ASYNC_CONNECT_ARGS,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
