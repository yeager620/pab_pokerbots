import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.bot import Bot, BotLanguage, BotStatus
from ..submission.bot_registry import BotRegistry


class TestBotRegistry:
    """Test cases for BotRegistry."""
    
    @pytest.mark.asyncio
    async def test_create_bot(self, db_session: AsyncSession):
        """Test creating a new bot."""
        registry = BotRegistry(db_session)
        
        bot = await registry.create_bot(
            user_id="test_user",
            name="test_bot",
            language=BotLanguage.PYTHON,
            version="1.0.0",
            description="Test bot"
        )
        
        assert bot.id is not None
        assert bot.user_id == "test_user"
        assert bot.name == "test_bot"
        assert bot.language == BotLanguage.PYTHON
        assert bot.version == "1.0.0"
        assert bot.status == BotStatus.SUBMITTED
    
    @pytest.mark.asyncio
    async def test_create_duplicate_bot_raises_error(self, db_session: AsyncSession):
        """Test that creating a duplicate bot raises an error."""
        registry = BotRegistry(db_session)
        
        # Create first bot
        await registry.create_bot(
            user_id="test_user",
            name="test_bot",
            language=BotLanguage.PYTHON,
            version="1.0.0"
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await registry.create_bot(
                user_id="test_user",
                name="test_bot",
                language=BotLanguage.PYTHON,
                version="1.0.0"
            )
    
    @pytest.mark.asyncio
    async def test_get_bot_by_id(self, db_session: AsyncSession, sample_bot: Bot):
        """Test getting a bot by ID."""
        registry = BotRegistry(db_session)
        
        retrieved_bot = await registry.get_bot_by_id(sample_bot.id)
        
        assert retrieved_bot is not None
        assert retrieved_bot.id == sample_bot.id
        assert retrieved_bot.name == sample_bot.name
    
    @pytest.mark.asyncio
    async def test_get_bot_by_id_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent bot returns None."""
        registry = BotRegistry(db_session)
        
        retrieved_bot = await registry.get_bot_by_id(99999)
        
        assert retrieved_bot is None
    
    @pytest.mark.asyncio
    async def test_get_bots_by_user(self, db_session: AsyncSession):
        """Test getting all bots for a user."""
        registry = BotRegistry(db_session)
        
        # Create multiple bots for same user
        bot1 = await registry.create_bot("user1", "bot1", BotLanguage.PYTHON, "1.0.0")
        bot2 = await registry.create_bot("user1", "bot2", BotLanguage.RUST, "1.0.0")
        bot3 = await registry.create_bot("user2", "bot3", BotLanguage.JAVA, "1.0.0")
        
        user1_bots = await registry.get_bots_by_user("user1")
        user2_bots = await registry.get_bots_by_user("user2")
        
        assert len(user1_bots) == 2
        assert len(user2_bots) == 1
        assert {bot.name for bot in user1_bots} == {"bot1", "bot2"}
        assert user2_bots[0].name == "bot3"
    
    @pytest.mark.asyncio
    async def test_update_bot_status(self, db_session: AsyncSession, sample_bot: Bot):
        """Test updating bot status."""
        registry = BotRegistry(db_session)
        
        updated_bot = await registry.update_bot_status(
            sample_bot.id, 
            BotStatus.ACTIVE, 
            "Validation successful"
        )
        
        assert updated_bot is not None
        assert updated_bot.status == BotStatus.ACTIVE
        assert updated_bot.validation_message == "Validation successful"
        assert updated_bot.last_validated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_active_bots(self, db_session: AsyncSession):
        """Test getting active bots."""
        registry = BotRegistry(db_session)
        
        # Create bots with different statuses
        bot1 = await registry.create_bot("user1", "bot1", BotLanguage.PYTHON, "1.0.0")
        bot2 = await registry.create_bot("user1", "bot2", BotLanguage.PYTHON, "1.0.0")
        bot3 = await registry.create_bot("user1", "bot3", BotLanguage.PYTHON, "1.0.0")
        
        # Set different statuses
        await registry.update_bot_status(bot1.id, BotStatus.ACTIVE)
        await registry.update_bot_status(bot2.id, BotStatus.ACTIVE)
        await registry.update_bot_status(bot3.id, BotStatus.FAILED)
        
        active_bots = await registry.get_active_bots()
        
        assert len(active_bots) == 2
        assert all(bot.status == BotStatus.ACTIVE for bot in active_bots)
    
    @pytest.mark.asyncio
    async def test_search_bots(self, db_session: AsyncSession):
        """Test searching bots with filters."""
        registry = BotRegistry(db_session)
        
        # Create bots with different attributes
        await registry.create_bot("user1", "python_bot", BotLanguage.PYTHON, "1.0.0", "A Python bot")
        await registry.create_bot("user1", "rust_bot", BotLanguage.RUST, "1.0.0", "A Rust bot")
        await registry.create_bot("user1", "test_bot", BotLanguage.JAVA, "1.0.0", "Testing bot")
        
        # Search by language
        python_bots = await registry.search_bots(language=BotLanguage.PYTHON)
        assert len(python_bots) == 1
        assert python_bots[0].name == "python_bot"
        
        # Search by query
        test_bots = await registry.search_bots(query="test")
        assert len(test_bots) == 1
        assert test_bots[0].name == "test_bot"
        
        # Search with limit
        limited_bots = await registry.search_bots(limit=2)
        assert len(limited_bots) == 2
    
    @pytest.mark.asyncio
    async def test_add_bot_file(self, db_session: AsyncSession, sample_bot: Bot):
        """Test adding a file to a bot."""
        registry = BotRegistry(db_session)
        
        file_content = b"print('Hello, world!')"
        bot_file = await registry.add_bot_file(
            sample_bot.id,
            "bot_main.py",
            file_content
        )
        
        assert bot_file.bot_id == sample_bot.id
        assert bot_file.file_path == "bot_main.py"
        assert bot_file.file_size == len(file_content)
        assert len(bot_file.file_hash) == 64  # SHA256 hash length
    
    @pytest.mark.asyncio
    async def test_add_bot_dependency(self, db_session: AsyncSession, sample_bot: Bot):
        """Test adding a dependency to a bot."""
        registry = BotRegistry(db_session)
        
        dependency = await registry.add_bot_dependency(
            sample_bot.id,
            "numpy",
            "1.21.0"
        )
        
        assert dependency.bot_id == sample_bot.id
        assert dependency.dependency_name == "numpy"
        assert dependency.version == "1.21.0"
    
    @pytest.mark.asyncio
    async def test_delete_bot(self, db_session: AsyncSession, sample_bot: Bot):
        """Test deleting a bot."""
        registry = BotRegistry(db_session)
        
        # Verify bot exists
        bot = await registry.get_bot_by_id(sample_bot.id)
        assert bot is not None
        
        # Delete bot
        success = await registry.delete_bot(sample_bot.id)
        assert success is True
        
        # Verify bot is deleted
        deleted_bot = await registry.get_bot_by_id(sample_bot.id)
        assert deleted_bot is None
    
    @pytest.mark.asyncio
    async def test_get_bot_statistics_summary(self, db_session: AsyncSession):
        """Test getting bot statistics summary."""
        registry = BotRegistry(db_session)
        
        # Create bots with different languages and statuses
        await registry.create_bot("user1", "bot1", BotLanguage.PYTHON, "1.0.0")
        await registry.create_bot("user1", "bot2", BotLanguage.RUST, "1.0.0")
        await registry.create_bot("user1", "bot3", BotLanguage.PYTHON, "1.0.0")
        
        stats = await registry.get_bot_statistics_summary()
        
        assert stats["total_bots"] == 3
        assert "status_distribution" in stats
        assert "language_distribution" in stats
        assert stats["language_distribution"][BotLanguage.PYTHON.value] == 2
        assert stats["language_distribution"][BotLanguage.RUST.value] == 1