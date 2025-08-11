import asyncio
import pytest
import tempfile
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from models.core import Base



TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_bot():
    import zipfile
    import io
    
    bot_code = '''
def get_action(game_state, legal_actions):
    if "CHECK" in legal_actions:
        return "CHECK"
    elif "CALL" in legal_actions:
        return "CALL"
    else:
        return "FOLD"

if __name__ == "__main__":
    pass
'''
    
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, 'w') as zf:
        zf.writestr("bot_main.py", bot_code)
    
    return archive_buffer.getvalue()