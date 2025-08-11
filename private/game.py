"""
Simplified poker game engine and match execution.
Core game logic with essential features only.
"""

import random
import asyncio
from datetime import datetime
import docker
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from models.core import Match, Bot, MatchStatus, calculate_elo_change


class PokerAction(Enum):
    FOLD = "F"
    CALL = "C" 
    CHECK = "K"
    RAISE = "R"


@dataclass
class GameState:
    round_num: int = 1
    button: int = 0
    street: int = 0
    pots: List[int] = None
    stacks: List[int] = None
    
    def __post_init__(self):
        if self.pots is None:
            self.pots = [1, 2]
        if self.stacks is None:
            self.stacks = [399, 398]


class PokerGame:
    """Simplified poker game logic."""
    
    STARTING_STACK = 400
    SMALL_BLIND = 1
    BIG_BLIND = 2
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        self.reset()
    
    def reset(self):
        """Reset for new game."""
        self.state = GameState()
        self.is_finished = False
        self.winner = None
        self.final_scores = [0, 0]
    
    def get_legal_actions(self) -> List[PokerAction]:
        """Get legal actions for current player."""
        active_player = self.state.button % 2
        continue_cost = self.state.pots[1-active_player] - self.state.pots[active_player]
        
        if continue_cost == 0:

            if self.state.stacks[0] == 0 or self.state.stacks[1] == 0:
                return [PokerAction.CHECK, PokerAction.FOLD]
            return [PokerAction.CHECK, PokerAction.RAISE, PokerAction.FOLD]
        else:

            if continue_cost >= self.state.stacks[active_player]:
                return [PokerAction.FOLD, PokerAction.CALL]
            return [PokerAction.FOLD, PokerAction.CALL, PokerAction.RAISE]
    
    def apply_action(self, action: PokerAction, amount: int = 0) -> bool:
        """Apply action and return True if game continues."""
        active_player = self.state.button % 2
        
        if action == PokerAction.FOLD:
            self.is_finished = True
            self.winner = 1 - active_player

            self.final_scores[self.winner] = sum(self.state.pots)
            self.final_scores[1 - self.winner] = -sum(self.state.pots)
            return False
        
        elif action == PokerAction.CALL:
            continue_cost = self.state.pots[1-active_player] - self.state.pots[active_player]
            self.state.stacks[active_player] -= continue_cost
            self.state.pots[active_player] += continue_cost
            

            if self.state.button > 0:
                return self._advance_street()
            else:
                self.state.button = 1
                return True
        
        elif action == PokerAction.CHECK:
            if self.state.button > 0:
                return self._advance_street()
            else:
                self.state.button = 1
                return True
        
        elif action == PokerAction.RAISE:

            bet_amount = amount - self.state.pots[active_player]
            self.state.stacks[active_player] -= bet_amount
            self.state.pots[active_player] = amount
            self.state.button = 1 - active_player
            return True
        
        return True
    
    def _advance_street(self) -> bool:
        """Advance to next street or end hand."""
        if self.state.street >= 3:
            self._finish_hand()
            return False
        
        self.state.street += 1
        self.state.button = 0
        return True
    
    def _finish_hand(self):
        """Finish hand at showdown."""
        self.is_finished = True

        self.winner = random.randint(0, 1)
        total_pot = sum(self.state.pots)
        self.final_scores[self.winner] = total_pot // 2
        self.final_scores[1 - self.winner] = -(total_pot // 2)


class BotRunner:
    """Runs bots in Docker containers."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_containers = {}
    
    async def start_bot(self, bot_id: int, bot_files_dir: str, language: str) -> str:
        """Start bot container and return container ID."""
        try:

            images = {
                "python": "python:3.13-slim",
                "rust": "rust:1.75-slim", 
                "java": "openjdk:17-slim",
                "cpp": "gcc:11-slim"
            }
            
            container = self.docker_client.containers.run(
                image=images.get(language, "python:3.13-slim"),
                command=["sleep", "300"],
                volumes={bot_files_dir: {"bind": "/app", "mode": "ro"}},
                working_dir="/app",
                mem_limit="256m",
                cpu_quota=50000,
                network_mode="none",
                detach=True,
                remove=True
            )
            
            self.active_containers[bot_id] = container
            return container.id
            
        except Exception as e:
            raise RuntimeError(f"Failed to start bot container: {str(e)}")
    
    async def stop_bot(self, bot_id: int):
        """Stop bot container."""
        if bot_id in self.active_containers:
            container = self.active_containers[bot_id]
            try:
                container.stop(timeout=5)
            except:
                pass
            del self.active_containers[bot_id]
    
    async def get_bot_action(self, bot_id: int, game_state: GameState, legal_actions: List[PokerAction], timeout: int = 10) -> PokerAction:
        """Get action from bot (simplified)."""


        await asyncio.sleep(0.1)
        return random.choice(legal_actions)


class MatchRunner:
    """Runs matches between bots."""
    
    def __init__(self, bot_files_dir: str = "/tmp/pokerbots"):
        self.bot_files_dir = bot_files_dir
        self.bot_runner = BotRunner()
    
    async def run_match(self, db: AsyncSession, match_id: int) -> Dict[str, Any]:
        """Run a complete match between two bots."""

        match = await db.get(Match, match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        bot1 = await db.get(Bot, match.bot1_id)
        bot2 = await db.get(Bot, match.bot2_id)
        

        match.status = MatchStatus.RUNNING
        match.started_at = datetime.now()
        await db.commit()
        
        try:

            container1 = await self.bot_runner.start_bot(
                bot1.id, bot1.file_path, bot1.language.value
            )
            container2 = await self.bot_runner.start_bot(
                bot2.id, bot2.file_path, bot2.language.value
            )
            

            game = PokerGame()
            game_log = []
            
            hands_played = 0
            max_hands = 100
            
            while hands_played < max_hands and not game.is_finished:

                active_player = game.state.button % 2
                bot_id = bot1.id if active_player == 0 else bot2.id
                
                legal_actions = game.get_legal_actions()
                action = await self.bot_runner.get_bot_action(bot_id, game.state, legal_actions)
                

                game_log.append({
                    "hand": hands_played,
                    "player": active_player,
                    "action": action.value,
                    "game_state": game.state.__dict__.copy()
                })
                

                continues = game.apply_action(action)
                if not continues:
                    hands_played += 1
                    if hands_played < max_hands:
                        game.reset()
            

            if game.winner is not None:
                winner_id = bot1.id if game.winner == 0 else bot2.id
                match.winner_id = winner_id
                match.bot1_score = game.final_scores[0]
                match.bot2_score = game.final_scores[1]
            

            await self._update_ratings(db, match)
            

            match.status = MatchStatus.COMPLETED
            match.completed_at = datetime.now()
            match.game_log = {"hands": hands_played, "actions": game_log}
            
            await db.commit()
            
            result = {
                "match_id": match_id,
                "winner_id": match.winner_id,
                "scores": [match.bot1_score, match.bot2_score],
                "hands_played": hands_played
            }
            
            return result
            
        except Exception as e:
            match.status = MatchStatus.FAILED
            await db.commit()
            raise
            
        finally:

            await self.bot_runner.stop_bot(bot1.id)
            await self.bot_runner.stop_bot(bot2.id)
    
    async def _update_ratings(self, db: AsyncSession, match: Match):
        """Update ELO ratings after match."""
        if match.winner_id:
            bot1 = await db.get(Bot, match.bot1_id)
            bot2 = await db.get(Bot, match.bot2_id)
            
            if match.winner_id == bot1.id:
                winner_change, loser_change = calculate_elo_change(bot1.rating, bot2.rating)
                bot1.rating += winner_change
                bot2.rating += loser_change
            else:
                winner_change, loser_change = calculate_elo_change(bot2.rating, bot1.rating)
                bot2.rating += winner_change
                bot1.rating += loser_change