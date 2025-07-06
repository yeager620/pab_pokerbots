import pytest
from unittest.mock import Mock, AsyncMock

from ..models.tournament import Tournament, TournamentFormat, TournamentStatus
from ..models.bot import BotStatus
from ..tournament.tournament_scheduler import TournamentScheduler


class TestTournamentScheduler:
    """Test cases for TournamentScheduler."""
    
    @pytest.mark.asyncio
    async def test_create_tournament(self, tournament_scheduler: TournamentScheduler):
        """Test creating a new tournament."""
        tournament = await tournament_scheduler.create_tournament(
            name="Test Tournament",
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=8,
            description="Test tournament"
        )
        
        assert tournament.id is not None
        assert tournament.name == "Test Tournament"
        assert tournament.format == TournamentFormat.SINGLE_ELIMINATION
        assert tournament.max_participants == 8
        assert tournament.status == TournamentStatus.CREATED
    
    @pytest.mark.asyncio
    async def test_register_bot(self, tournament_scheduler: TournamentScheduler, sample_tournament: Tournament, sample_bot):
        """Test registering a bot for a tournament."""
        # Update bot status to active
        await tournament_scheduler._db_session.execute(
            tournament_scheduler._db_session.query(type(sample_bot))
            .filter_by(id=sample_bot.id)
            .update({"status": BotStatus.ACTIVE})
        )
        await tournament_scheduler._db_session.commit()
        
        success = await tournament_scheduler.register_bot(sample_tournament.id, sample_bot.id)
        
        assert success is True
        
        # Verify participant was created
        participants = await tournament_scheduler._get_tournament_participants(sample_tournament.id)
        assert len(participants) == 1
        assert participants[0].bot_id == sample_bot.id
    
    @pytest.mark.asyncio
    async def test_register_bot_tournament_full(self, tournament_scheduler: TournamentScheduler, sample_bots):
        """Test registering a bot when tournament is full."""
        # Create tournament with max 2 participants
        tournament = await tournament_scheduler.create_tournament(
            name="Small Tournament",
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=2
        )
        
        # Set bots to active
        for bot in sample_bots[:3]:
            bot.status = BotStatus.ACTIVE
        await tournament_scheduler._db_session.commit()
        
        # Register first two bots
        success1 = await tournament_scheduler.register_bot(tournament.id, sample_bots[0].id)
        success2 = await tournament_scheduler.register_bot(tournament.id, sample_bots[1].id)
        
        assert success1 is True
        assert success2 is True
        
        # Try to register third bot (should fail)
        success3 = await tournament_scheduler.register_bot(tournament.id, sample_bots[2].id)
        assert success3 is False
    
    @pytest.mark.asyncio
    async def test_register_duplicate_bot(self, tournament_scheduler: TournamentScheduler, sample_tournament: Tournament, sample_bot):
        """Test registering the same bot twice."""
        # Update bot status to active
        sample_bot.status = BotStatus.ACTIVE
        await tournament_scheduler._db_session.commit()
        
        # Register bot first time
        success1 = await tournament_scheduler.register_bot(sample_tournament.id, sample_bot.id)
        assert success1 is True
        
        # Try to register same bot again
        success2 = await tournament_scheduler.register_bot(sample_tournament.id, sample_bot.id)
        assert success2 is False
    
    @pytest.mark.asyncio
    async def test_unregister_bot(self, tournament_scheduler: TournamentScheduler, sample_tournament: Tournament, sample_bot):
        """Test unregistering a bot from a tournament."""
        # Register bot first
        sample_bot.status = BotStatus.ACTIVE
        await tournament_scheduler._db_session.commit()
        
        await tournament_scheduler.register_bot(sample_tournament.id, sample_bot.id)
        
        # Unregister bot
        success = await tournament_scheduler.unregister_bot(sample_tournament.id, sample_bot.id)
        assert success is True
        
        # Verify participant was removed
        participants = await tournament_scheduler._get_tournament_participants(sample_tournament.id)
        assert len(participants) == 0
    
    @pytest.mark.asyncio
    async def test_start_tournament_single_elimination(self, tournament_scheduler: TournamentScheduler, sample_bots):
        """Test starting a single elimination tournament."""
        # Create tournament
        tournament = await tournament_scheduler.create_tournament(
            name="Test Tournament",
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=4
        )
        
        # Set bots to active and register them
        for bot in sample_bots:
            bot.status = BotStatus.ACTIVE
        await tournament_scheduler._db_session.commit()
        
        for bot in sample_bots:
            await tournament_scheduler.register_bot(tournament.id, bot.id)
        
        # Close registration
        await tournament_scheduler._update_tournament_status(tournament.id, TournamentStatus.REGISTRATION_CLOSED)
        
        # Start tournament
        result = await tournament_scheduler.start_tournament(tournament.id)
        
        assert result.success is True
        assert result.matches_created > 0
        
        # Verify tournament status
        updated_tournament = await tournament_scheduler._get_tournament(tournament.id)
        assert updated_tournament.status == TournamentStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_start_tournament_insufficient_participants(self, tournament_scheduler: TournamentScheduler, sample_tournament: Tournament):
        """Test starting a tournament with insufficient participants."""
        # Close registration without registering enough bots
        await tournament_scheduler._update_tournament_status(sample_tournament.id, TournamentStatus.REGISTRATION_CLOSED)
        
        result = await tournament_scheduler.start_tournament(sample_tournament.id)
        
        assert result.success is False
        assert "Need at least 2 participants" in result.message
    
    @pytest.mark.asyncio
    async def test_start_tournament_round_robin(self, tournament_scheduler: TournamentScheduler, sample_bots):
        """Test starting a round robin tournament."""
        # Create round robin tournament
        tournament = await tournament_scheduler.create_tournament(
            name="Round Robin Tournament",
            format=TournamentFormat.ROUND_ROBIN,
            max_participants=4,
            config={"rounds": 1}
        )
        
        # Register bots
        for bot in sample_bots:
            bot.status = BotStatus.ACTIVE
            await tournament_scheduler.register_bot(tournament.id, bot.id)
        await tournament_scheduler._db_session.commit()
        
        # Close registration and start
        await tournament_scheduler._update_tournament_status(tournament.id, TournamentStatus.REGISTRATION_CLOSED)
        result = await tournament_scheduler.start_tournament(tournament.id)
        
        assert result.success is True
        # Round robin with 4 players should create 6 matches (4 choose 2)
        assert result.matches_created == 6
    
    @pytest.mark.asyncio
    async def test_get_tournament_standings(self, tournament_scheduler: TournamentScheduler, sample_tournament: Tournament, sample_bots):
        """Test getting tournament standings."""
        # Register bots
        for bot in sample_bots:
            bot.status = BotStatus.ACTIVE
            await tournament_scheduler.register_bot(sample_tournament.id, bot.id)
        await tournament_scheduler._db_session.commit()
        
        standings = await tournament_scheduler.get_tournament_standings(sample_tournament.id)
        
        assert len(standings) == len(sample_bots)
        
        # Check standings structure
        for standing in standings:
            assert "bot_id" in standing
            assert "bot_name" in standing
            assert "user_id" in standing
            assert "wins" in standing
            assert "losses" in standing
            assert "rank" in standing
        
        # Rankings should be assigned
        ranks = [standing["rank"] for standing in standings]
        assert ranks == list(range(1, len(sample_bots) + 1))
    
    @pytest.mark.asyncio
    async def test_swiss_system_round_generation(self, tournament_scheduler: TournamentScheduler, sample_bots):
        """Test Swiss system round generation."""
        # Create Swiss tournament
        tournament = await tournament_scheduler.create_tournament(
            name="Swiss Tournament",
            format=TournamentFormat.SWISS,
            max_participants=4,
            config={"max_rounds": 3}
        )
        
        # Register bots
        for bot in sample_bots:
            bot.status = BotStatus.ACTIVE
            await tournament_scheduler.register_bot(tournament.id, bot.id)
        await tournament_scheduler._db_session.commit()
        
        # Start tournament (should create first round)
        await tournament_scheduler._update_tournament_status(tournament.id, TournamentStatus.REGISTRATION_CLOSED)
        result = await tournament_scheduler.start_tournament(tournament.id)
        
        assert result.success is True
        # First round with 4 players should create 2 matches
        assert result.matches_created == 2
        
        # Test scheduling next round
        next_result = await tournament_scheduler.schedule_next_round(tournament.id)
        # Should fail because current round is not complete
        assert next_result.success is False
        assert "not yet complete" in next_result.message
    
    @pytest.mark.asyncio
    async def test_bracket_validation(self, tournament_scheduler: TournamentScheduler):
        """Test bracket validation."""
        from ..tournament.bracket_generator import MatchPairing
        
        # Create valid bracket
        valid_bracket = [
            MatchPairing(1, 1, 1, 2),
            MatchPairing(1, 2, 3, 4),
            MatchPairing(2, 1, None, None)  # TBD based on first round
        ]
        
        issues = tournament_scheduler.bracket_generator.validate_bracket(valid_bracket)
        assert len(issues) == 0
        
        # Create invalid bracket (duplicate match numbers)
        invalid_bracket = [
            MatchPairing(1, 1, 1, 2),
            MatchPairing(1, 1, 3, 4),  # Duplicate match number
        ]
        
        issues = tournament_scheduler.bracket_generator.validate_bracket(invalid_bracket)
        assert len(issues) > 0
        assert "Duplicate match number" in issues[0]