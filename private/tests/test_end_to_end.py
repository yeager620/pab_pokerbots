"""
End-to-end integration tests for the simplified poker bot infrastructure.
Tests the complete workflow from bot submission to tournament completion.
"""

import asyncio
import pytest
import tempfile
import zipfile
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from models.core import init_db, get_db, Bot, Tournament, Match, BotLanguage, BotStatus, TournamentStatus
from bots import BotManager
from tournaments import TournamentManager
from game import MatchRunner
from analytics import Analytics
from config import config



TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    

    from models import core
    original_engine = core.engine
    core.engine = engine
    

    await init_db()
    
    yield engine
    

    core.engine = original_engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_db):
    """Create test database session."""
    TestSessionLocal = async_sessionmaker(
        test_db,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_bot():
    """Create a sample Python bot archive."""
    bot_code = '''
def get_action(game_state, legal_actions):
    """Simple bot that always checks/calls."""
    if "CHECK" in legal_actions:
        return "CHECK"
    elif "CALL" in legal_actions:
        return "CALL"
    else:
        return "FOLD"

if __name__ == "__main__":
    pass
'''
    
    archive_buffer = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    with zipfile.ZipFile(archive_buffer.name, 'w') as zf:
        zf.writestr("bot_main.py", bot_code)
    
    with open(archive_buffer.name, 'rb') as f:
        return f.read()


@pytest.fixture
def bot_manager(temp_storage):
    """Create bot manager with temporary storage."""
    return BotManager(str(temp_storage))


@pytest.fixture  
def tournament_manager(temp_storage):
    """Create tournament manager."""
    return TournamentManager(str(temp_storage))


@pytest.fixture
def match_runner(temp_storage):
    """Create match runner."""
    return MatchRunner(str(temp_storage))


@pytest.fixture
def analytics():
    """Create analytics instance."""
    return Analytics()


class TestEndToEndWorkflow:
    """Complete end-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_tournament_workflow(
        self, 
        db_session: AsyncSession,
        bot_manager: BotManager,
        tournament_manager: TournamentManager,
        match_runner: MatchRunner,
        analytics: Analytics,
        sample_python_bot: bytes
    ):
        """Test complete workflow: submit bots -> create tournament -> run matches -> check results."""
        

        print("📤 Submitting bots...")
        bots = []
        for i in range(4):
            bot = await bot_manager.submit_bot(
                db_session,
                user_id=f"user_{i}",
                name=f"TestBot_{i}",
                language=BotLanguage.PYTHON,
                version="1.0",
                bot_archive=sample_python_bot
            )
            assert bot.status == BotStatus.ACTIVE
            bots.append(bot)
            print(f"✅ Bot {bot.name} submitted successfully (ID: {bot.id})")
        

        print("\n🏆 Creating tournament...")
        tournament = await tournament_manager.create_tournament(
            db_session,
            name="Test Tournament",
            max_participants=4
        )
        assert tournament.status == TournamentStatus.OPEN
        print(f"✅ Tournament '{tournament.name}' created (ID: {tournament.id})")
        

        print("\n📝 Registering bots...")
        for bot in bots:
            success = await tournament_manager.register_bot(db_session, tournament.id, bot.id)
            assert success
            print(f"✅ Bot {bot.name} registered")
        

        print("\n🚀 Starting tournament...")
        result = await tournament_manager.start_tournament(db_session, tournament.id)
        assert result["success"]
        print(f"✅ Tournament started: {result['message']}")
        

        print("\n⏳ Waiting for tournament completion...")
        max_wait = 60
        wait_time = 0
        while wait_time < max_wait:
            await db_session.refresh(tournament)
            if tournament.status == TournamentStatus.COMPLETED:
                break
            await asyncio.sleep(1)
            wait_time += 1
        
        assert tournament.status == TournamentStatus.COMPLETED, "Tournament should complete"
        print("✅ Tournament completed!")
        

        print("\n📊 Checking results...")
        

        standings = await tournament_manager.get_tournament_standings(db_session, tournament.id)
        assert len(standings) == 4
        assert standings[0]["rank"] == 1
        print(f"🏆 Winner: {standings[0]['bot_name']}")
        

        matches = await tournament_manager.get_tournament_matches(db_session, tournament.id)
        completed_matches = [m for m in matches if m["status"] == "completed"]
        assert len(completed_matches) >= 3
        print(f"✅ {len(completed_matches)} matches completed")
        

        leaderboard = await analytics.get_leaderboard(db_session, limit=10)
        assert len(leaderboard) == 4
        assert all(bot["matches_played"] > 0 for bot in leaderboard)
        print("✅ Leaderboard updated with new ratings")
        

        global_stats = await analytics.get_global_stats(db_session)
        assert global_stats["total_bots"] == 4
        assert global_stats["total_matches"] >= 3
        print(f"📈 Global stats: {global_stats}")
        
        print("\n🎉 End-to-end test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_bot_submission_validation(
        self,
        db_session: AsyncSession,
        bot_manager: BotManager
    ):
        """Test bot validation during submission."""
        

        valid_bot_code = 'print("Hello, World!")'
        archive_buffer = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        with zipfile.ZipFile(archive_buffer.name, 'w') as zf:
            zf.writestr("bot_main.py", valid_bot_code)
        
        with open(archive_buffer.name, 'rb') as f:
            valid_archive = f.read()
        
        bot = await bot_manager.submit_bot(
            db_session,
            user_id="test_user",
            name="ValidBot",
            language=BotLanguage.PYTHON,
            version="1.0",
            bot_archive=valid_archive
        )
        assert bot.status == BotStatus.ACTIVE
        

        invalid_archive_buffer = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        with zipfile.ZipFile(invalid_archive_buffer.name, 'w') as zf:
            zf.writestr("wrong_file.txt", "not a bot")
        
        with open(invalid_archive_buffer.name, 'rb') as f:
            invalid_archive = f.read()
        
        with pytest.raises(ValueError, match="Missing required file"):
            await bot_manager.submit_bot(
                db_session,
                user_id="test_user",
                name="InvalidBot",
                language=BotLanguage.PYTHON,
                version="1.0",
                bot_archive=invalid_archive
            )
    
    @pytest.mark.asyncio
    async def test_tournament_edge_cases(
        self,
        db_session: AsyncSession,
        bot_manager: BotManager,
        tournament_manager: TournamentManager,
        sample_python_bot: bytes
    ):
        """Test tournament edge cases."""
        

        tournament = await tournament_manager.create_tournament(
            db_session,
            name="Edge Case Tournament",
            max_participants=8
        )
        

        result = await tournament_manager.start_tournament(db_session, tournament.id)
        assert not result["success"]
        assert "at least 2 participants" in result["error"]
        

        bot = await bot_manager.submit_bot(
            db_session,
            user_id="user_1",
            name="LoneBot",
            language=BotLanguage.PYTHON,
            version="1.0",
            bot_archive=sample_python_bot
        )
        await tournament_manager.register_bot(db_session, tournament.id, bot.id)
        

        result = await tournament_manager.start_tournament(db_session, tournament.id)
        assert not result["success"]
        assert "at least 2 participants" in result["error"]


class TestProductionReadiness:
    """Tests to verify production readiness."""
    
    @pytest.mark.asyncio
    async def test_concurrent_bot_submissions(
        self,
        db_session: AsyncSession,
        bot_manager: BotManager,
        sample_python_bot: bytes
    ):
        """Test handling concurrent bot submissions."""
        
        async def submit_bot(i):
            return await bot_manager.submit_bot(
                db_session,
                user_id=f"concurrent_user_{i}",
                name=f"ConcurrentBot_{i}",
                language=BotLanguage.PYTHON,
                version="1.0",
                bot_archive=sample_python_bot
            )
        

        tasks = [submit_bot(i) for i in range(5)]
        bots = await asyncio.gather(*tasks)
        

        assert len(bots) == 5
        assert all(bot.status == BotStatus.ACTIVE for bot in bots)
        assert len(set(bot.id for bot in bots)) == 5
    
    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        db_session: AsyncSession,
        bot_manager: BotManager
    ):
        """Test error handling throughout the system."""
        

        with pytest.raises(ValueError):
            await bot_manager.submit_bot(
                db_session,
                user_id="error_user",
                name="ErrorBot",
                language=BotLanguage.PYTHON,
                version="1.0",
                bot_archive=b"not a zip file"
            )
        

        malicious_archive = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        with zipfile.ZipFile(malicious_archive.name, 'w') as zf:
            zf.writestr("../../../etc/passwd", "malicious content")
        
        with open(malicious_archive.name, 'rb') as f:
            malicious_data = f.read()
        
        with pytest.raises(ValueError, match="Unsafe file path"):
            await bot_manager.submit_bot(
                db_session,
                user_id="malicious_user",
                name="MaliciousBot",
                language=BotLanguage.PYTHON,
                version="1.0",
                bot_archive=malicious_data
            )



async def run_integration_test():
    """Run a quick integration test for manual testing."""
    print("🧪 Running manual integration test...")
    


    pass


if __name__ == "__main__":

    asyncio.run(run_integration_test())