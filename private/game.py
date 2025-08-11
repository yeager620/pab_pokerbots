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
        # Track match vs hand completion separately
        self.is_finished = False  # Match finished (when player runs out of chips)
        self.hands_played = 0
        self.match_scores = [0, 0]  # Running match scores
        self.reset()
    
    def reset(self):
        """Reset for new hand."""
        self.state = GameState()
        self.state.round_num = self.hands_played + 1
        self.hand_finished = False
        self.winner = None
        self.final_scores = [0, 0]  # Hand scores
    
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
            # End this hand, but not the match
            self.hand_finished = True
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
    
    def complete_hand(self):
        """Complete the current hand and update match scores."""
        if self.winner is not None:
            # Update running match scores
            self.match_scores[0] += self.final_scores[0]
            self.match_scores[1] += self.final_scores[1]
            self.hands_played += 1
            
            # Check if either player is out of chips (match over)
            if self.state.stacks[0] <= 0:
                self.is_finished = True
                self.match_winner = 1
            elif self.state.stacks[1] <= 0:
                self.is_finished = True 
                self.match_winner = 0
        
        return not self.is_finished
    
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
            detailed_log = []
            
            hands_played = 0
            max_hands = 100
            
            # Log initial game state
            detailed_log.append({
                "event": "match_start",
                "bot1_name": bot1.name,
                "bot2_name": bot2.name,
                "starting_stacks": [game.STARTING_STACK, game.STARTING_STACK],
                "max_hands": max_hands
            })
            
            # Main game loop - play multiple hands until match ends
            while game.hands_played < max_hands and not game.is_finished:
                
                # Start new hand
                current_hand = game.hands_played + 1
                detailed_log.append({
                    "event": "hand_start",
                    "hand_number": current_hand,
                    "stacks_before": game.state.stacks.copy(),
                    "button_player": game.state.button,
                    "blinds_posted": {"small_blind": game.SMALL_BLIND, "big_blind": game.BIG_BLIND}
                })
                
                # Play the hand until it's finished
                while not game.hand_finished:
                    active_player = game.state.button % 2
                    bot_id = bot1.id if active_player == 0 else bot2.id
                    bot_name = bot1.name if active_player == 0 else bot2.name
                    
                    # Capture pre-action state
                    pre_action_state = {
                        "round_num": game.state.round_num,
                        "street": game.state.street,
                        "stacks": game.state.stacks.copy(),
                        "pots": game.state.pots.copy(),
                        "active_player": active_player,
                        "button": game.state.button
                    }
                    
                    legal_actions = game.get_legal_actions()
                    action = await self.bot_runner.get_bot_action(bot_id, game.state, legal_actions)
                    
                    # Calculate action details
                    continue_cost = 0
                    if action in [PokerAction.CALL, PokerAction.RAISE]:
                        continue_cost = game.state.pots[1-active_player] - game.state.pots[active_player]

                    # Log detailed action
                    detailed_log.append({
                        "event": "player_action",
                        "hand_number": current_hand,
                        "player": active_player,
                        "player_name": bot_name,
                        "action": action.value,
                        "legal_actions": [a.value for a in legal_actions],
                        "pre_action_state": pre_action_state,
                        "continue_cost": continue_cost,
                        "stack_before": game.state.stacks[active_player]
                    })

                    # Apply action and capture result
                    continues = game.apply_action(action)
                    
                    # Log post-action state
                    detailed_log.append({
                        "event": "action_result", 
                        "hand_number": current_hand,
                        "player": active_player,
                        "player_name": bot_name,
                        "action": action.value,
                        "stack_after": game.state.stacks[active_player],
                        "stack_change": game.state.stacks[active_player] - pre_action_state["stacks"][active_player],
                        "pots_after": game.state.pots.copy(),
                        "pot_total": sum(game.state.pots),
                        "game_continues": continues,
                        "hand_finished": game.hand_finished
                    })
                    
                    # Basic game log for compatibility
                    game_log.append({
                        "hand": current_hand,
                        "player": active_player,
                        "action": action.value,
                        "game_state": game.state.__dict__.copy()
                    })

                # Hand is finished, log the result
                winner_name = bot1.name if game.winner == 0 else bot2.name
                detailed_log.append({
                    "event": "hand_end",
                    "hand_number": current_hand,
                    "winner": game.winner,
                    "winner_name": winner_name,
                    "final_stacks": game.state.stacks.copy(),
                    "final_scores": game.final_scores.copy(),
                    "pot_won": sum(game.state.pots)
                })
                
                # Complete the hand and check if match should continue
                match_continues = game.complete_hand()
                if match_continues:
                    game.reset()  # Reset for next hand
            

            # Determine final match winner
            if game.is_finished and hasattr(game, 'match_winner'):
                winner_id = bot1.id if game.match_winner == 0 else bot2.id
                match.winner_id = winner_id
                match.bot1_score = game.match_scores[0]
                match.bot2_score = game.match_scores[1]
            elif game.match_scores[0] > game.match_scores[1]:
                match.winner_id = bot1.id
                match.bot1_score = game.match_scores[0]
                match.bot2_score = game.match_scores[1]
            else:
                match.winner_id = bot2.id
                match.bot1_score = game.match_scores[0]
                match.bot2_score = game.match_scores[1]
            

            await self._update_ratings(db, match)
            

            # Log final match results
            final_winner = 0 if match.winner_id == bot1.id else 1
            detailed_log.append({
                "event": "match_end",
                "total_hands": game.hands_played,
                "winner": final_winner,
                "winner_name": bot1.name if final_winner == 0 else bot2.name,
                "final_scores": game.match_scores.copy(),
                "final_stacks": game.state.stacks.copy()
            })
            
            match.status = MatchStatus.COMPLETED
            match.completed_at = datetime.now()
            match.game_log = {
                "hands": game.hands_played, 
                "actions": game_log,
                "detailed_log": detailed_log,
                "summary": {
                    "bot1_name": bot1.name,
                    "bot2_name": bot2.name,
                    "winner": bot1.name if final_winner == 0 else bot2.name,
                    "total_hands": game.hands_played,
                    "final_scores": game.match_scores.copy()
                }
            }
            
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