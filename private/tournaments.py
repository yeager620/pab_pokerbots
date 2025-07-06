"""
Simplified tournament management.
Single-elimination tournaments with basic bracket generation.
"""

import asyncio
import random
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .models.core import Tournament, Match, Bot, TournamentStatus, MatchStatus
from .game import MatchRunner


class TournamentManager:
    """Manages tournaments with simplified single-elimination format."""
    
    def __init__(self, bot_files_dir: str = "/tmp/pokerbots"):
        self.match_runner = MatchRunner(bot_files_dir)
    
    async def create_tournament(self, db: AsyncSession, name: str, max_participants: int = 8) -> Tournament:
        """Create a new tournament."""
        tournament = Tournament(
            name=name,
            max_participants=max_participants,
            status=TournamentStatus.OPEN
        )
        db.add(tournament)
        await db.commit()
        return tournament
    
    async def register_bot(self, db: AsyncSession, tournament_id: int, bot_id: int) -> bool:
        """Register a bot for a tournament."""
        tournament = await db.get(Tournament, tournament_id)
        if not tournament or tournament.status != TournamentStatus.OPEN:
            return False
        
        # Check if tournament is full
        if len(tournament.participants) >= tournament.max_participants:
            return False
        
        # Check if bot is already registered
        if bot_id in tournament.participants:
            return False
        
        # Add bot to participants
        tournament.participants = tournament.participants + [bot_id]
        await db.commit()
        return True
    
    async def start_tournament(self, db: AsyncSession, tournament_id: int) -> Dict[str, Any]:
        """Start tournament and generate first round matches."""
        tournament = await db.get(Tournament, tournament_id)
        if not tournament or tournament.status != TournamentStatus.OPEN:
            return {"success": False, "error": "Tournament not ready to start"}
        
        if len(tournament.participants) < 2:
            return {"success": False, "error": "Need at least 2 participants"}
        
        # Generate bracket
        matches = self._generate_bracket(tournament.participants)
        
        # Create match records
        for round_num, round_matches in enumerate(matches, 1):
            for bot1_id, bot2_id in round_matches:
                match = Match(
                    tournament_id=tournament_id,
                    bot1_id=bot1_id,
                    bot2_id=bot2_id,
                    status=MatchStatus.SCHEDULED
                )
                db.add(match)
        
        tournament.status = TournamentStatus.RUNNING
        await db.commit()
        
        # Start first round matches
        asyncio.create_task(self._run_tournament_matches(db, tournament_id))
        
        return {
            "success": True, 
            "message": f"Tournament started with {len(tournament.participants)} participants",
            "first_round_matches": len(matches[0]) if matches else 0
        }
    
    def _generate_bracket(self, participants: List[int]) -> List[List[tuple]]:
        """Generate single-elimination bracket."""
        # Shuffle participants for random seeding
        participants = participants.copy()
        random.shuffle(participants)
        
        # Pad to next power of 2 with byes
        tournament_size = 1
        while tournament_size < len(participants):
            tournament_size *= 2
        
        while len(participants) < tournament_size:
            participants.append(None)  # Bye
        
        # Generate rounds
        rounds = []
        current_round = participants
        
        while len(current_round) > 1:
            matches = []
            next_round = []
            
            for i in range(0, len(current_round), 2):
                p1, p2 = current_round[i], current_round[i+1]
                
                # Skip matches with byes
                if p1 is None:
                    next_round.append(p2)
                elif p2 is None:
                    next_round.append(p1)
                else:
                    matches.append((p1, p2))
                    next_round.append(None)  # Winner TBD
            
            if matches:
                rounds.append(matches)
            current_round = next_round
        
        return rounds
    
    async def _run_tournament_matches(self, db: AsyncSession, tournament_id: int):
        """Run all tournament matches sequentially."""
        while True:
            # Get next scheduled matches
            stmt = select(Match).where(
                Match.tournament_id == tournament_id,
                Match.status == MatchStatus.SCHEDULED
            )
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            if not matches:
                # Check if tournament is complete
                await self._check_tournament_completion(db, tournament_id)
                break
            
            # Run first available match
            match = matches[0]
            try:
                await self.match_runner.run_match(db, match.id)
                await self._advance_winner(db, match.id)
            except Exception as e:
                print(f"Match {match.id} failed: {e}")
                match.status = MatchStatus.FAILED
                await db.commit()
            
            # Small delay between matches
            await asyncio.sleep(1)
    
    async def _advance_winner(self, db: AsyncSession, completed_match_id: int):
        """Advance winner to next round."""
        completed_match = await db.get(Match, completed_match_id)
        if not completed_match or not completed_match.winner_id:
            return
        
        # Find next round match that needs this winner
        # Simplified: just mark winner in result
        pass
    
    async def _check_tournament_completion(self, db: AsyncSession, tournament_id: int):
        """Check if tournament is complete and update status."""
        stmt = select(Match).where(
            Match.tournament_id == tournament_id,
            Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.RUNNING])
        )
        result = await db.execute(stmt)
        remaining_matches = result.scalars().all()
        
        if not remaining_matches:
            # Tournament complete
            tournament = await db.get(Tournament, tournament_id)
            tournament.status = TournamentStatus.COMPLETED
            await db.commit()
    
    async def get_tournament_standings(self, db: AsyncSession, tournament_id: int) -> List[Dict[str, Any]]:
        """Get current tournament standings."""
        tournament = await db.get(Tournament, tournament_id)
        if not tournament:
            return []
        
        standings = []
        for bot_id in tournament.participants:
            bot = await db.get(Bot, bot_id)
            if bot:
                # Get bot's matches in this tournament
                stmt = select(Match).where(
                    Match.tournament_id == tournament_id,
                    (Match.bot1_id == bot_id) | (Match.bot2_id == bot_id),
                    Match.status == MatchStatus.COMPLETED
                )
                result = await db.execute(stmt)
                matches = result.scalars().all()
                
                wins = sum(1 for m in matches if m.winner_id == bot_id)
                losses = len(matches) - wins
                
                standings.append({
                    "bot_id": bot_id,
                    "bot_name": bot.name,
                    "user_id": bot.user_id,
                    "wins": wins,
                    "losses": losses,
                    "matches_played": len(matches)
                })
        
        # Sort by wins descending
        standings.sort(key=lambda x: x["wins"], reverse=True)
        
        # Add rankings
        for i, standing in enumerate(standings):
            standing["rank"] = i + 1
        
        return standings
    
    async def get_tournament_matches(self, db: AsyncSession, tournament_id: int) -> List[Dict[str, Any]]:
        """Get all matches for a tournament."""
        stmt = select(Match).where(Match.tournament_id == tournament_id)
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        match_data = []
        for match in matches:
            bot1 = await db.get(Bot, match.bot1_id)
            bot2 = await db.get(Bot, match.bot2_id)
            winner = await db.get(Bot, match.winner_id) if match.winner_id else None
            
            match_data.append({
                "id": match.id,
                "bot1_name": bot1.name if bot1 else "Unknown",
                "bot2_name": bot2.name if bot2 else "Unknown", 
                "status": match.status.value,
                "winner_name": winner.name if winner else None,
                "started_at": match.started_at,
                "completed_at": match.completed_at
            })
        
        return match_data