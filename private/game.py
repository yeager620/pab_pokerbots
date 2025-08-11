
import random
import asyncio
from datetime import datetime
import docker
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from models.core import Match, Bot, MatchStatus, calculate_elo_change


class PokerAction(Enum):
    FOLD = "F"
    CALL = "C" 
    CHECK = "K"
    RAISE = "R"


class Card:
    SUITS = ['S', 'H', 'D', 'C']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.value = self.RANKS.index(rank) + 2
    
    def __str__(self):
        return f"{self.rank}{self.suit}"
    
    def __repr__(self):
        return str(self)


class Deck:
    
    def __init__(self, seed: Optional[int] = None):
        self.cards = []
        self.shuffle()
    
    def shuffle(self):
        self.cards = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS]
        random.shuffle(self.cards)
    
    def deal(self) -> Card:
        if not self.cards:
            raise ValueError("Cannot deal from empty deck")
        return self.cards.pop()


class HandEvaluator:
    
    @staticmethod
    def evaluate_hand(hole_cards: List[Card], community_cards: List[Card]) -> Tuple[int, str]:
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            return (1, "High Card")
        
        best_strength = 0
        best_desc = "High Card"
        
        from itertools import combinations
        for combo in combinations(all_cards, 5):
            strength, desc = HandEvaluator._evaluate_5_cards(list(combo))
            if strength > best_strength:
                best_strength = strength
                best_desc = desc
        
        return (best_strength, best_desc)
    
    @staticmethod
    def _evaluate_5_cards(cards: List[Card]) -> Tuple[int, str]:
        if len(cards) != 5:
            return (1, "High Card")
        
        cards = sorted(cards, key=lambda c: c.value, reverse=True)
        values = [c.value for c in cards]
        suits = [c.suit for c in cards]
        
        is_flush = len(set(suits)) == 1
        
        is_straight = False
        if values == [14, 5, 4, 3, 2]:
            is_straight = True
            values = [5, 4, 3, 2, 1]
        elif values[0] - values[4] == 4 and len(set(values)) == 5:
            is_straight = True
        
        from collections import Counter
        counts = Counter(values)
        count_values = sorted(counts.values(), reverse=True)
        
        if is_straight and is_flush:
            if values[0] == 14:
                return (10, "Royal Flush")
            return (9, "Straight Flush")
        elif count_values == [4, 1]:
            return (8, "Four of a Kind")
        elif count_values == [3, 2]:
            return (7, "Full House")
        elif is_flush:
            return (6, "Flush")
        elif is_straight:
            return (5, "Straight")
        elif count_values == [3, 1, 1]:
            return (4, "Three of a Kind")
        elif count_values == [2, 2, 1]:
            return (3, "Two Pair")
        elif count_values == [2, 1, 1, 1]:
            return (2, "One Pair")
        else:
            return (1, "High Card")


@dataclass
class GameState:
    round_num: int = 1
    button: int = 0
    street: int = 0
    pot: int = 0
    stacks: List[int] = None
    hole_cards: List[List[Card]] = None
    community_cards: List[Card] = None
    current_bets: List[int] = None
    total_invested: List[int] = None
    
    def __post_init__(self):
        if self.stacks is None:
            self.stacks = [400, 400]
        if self.hole_cards is None:
            self.hole_cards = [[], []]
        if self.community_cards is None:
            self.community_cards = []
        if self.current_bets is None:
            self.current_bets = [0, 0]
        if self.total_invested is None:
            self.total_invested = [0, 0]


class PokerGame:
    
    STARTING_STACK = 400
    SMALL_BLIND = 1
    BIG_BLIND = 2
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        self.is_finished = False
        self.hands_played = 0
        self.match_scores = [0, 0]
        self.deck = Deck()
        self.evaluator = HandEvaluator()
        self.reset()
    
    def reset(self):
        current_stacks = getattr(self.state, 'stacks', [self.STARTING_STACK, self.STARTING_STACK]) if hasattr(self, 'state') else [self.STARTING_STACK, self.STARTING_STACK]
        
        self.state = GameState()
        self.state.stacks = current_stacks.copy()
        self.state.round_num = self.hands_played + 1
        self.hand_finished = False
        self.winner = None
        self.final_scores = [0, 0]
        self.active_player = 0
        self.last_raiser = None
        self.deck.shuffle()
        self._deal_hole_cards()
        self._post_blinds()
    
    def get_legal_actions(self) -> List[PokerAction]:
        if self.hand_finished:
            return []
        
        max_bet = max(self.state.current_bets)
        call_amount = max_bet - self.state.current_bets[self.active_player]
        
        actions = [PokerAction.FOLD]
        
        if call_amount == 0:
            actions.append(PokerAction.CHECK)
        else:
            if call_amount < self.state.stacks[self.active_player]:
                actions.append(PokerAction.CALL)
            elif call_amount >= self.state.stacks[self.active_player] and self.state.stacks[self.active_player] > 0:
                actions.append(PokerAction.CALL)
        
        if self.state.stacks[self.active_player] > call_amount:
            actions.append(PokerAction.RAISE)
        
        return actions
    
    def apply_action(self, action: PokerAction, amount: int = 0) -> bool:
        if self.hand_finished:
            return False
        
        if action == PokerAction.FOLD:
            self.hand_finished = True
            self.winner = 1 - self.active_player
            self.final_scores[self.winner] = self.state.pot - self.state.total_invested[self.winner]
            self.final_scores[1 - self.winner] = -self.state.total_invested[1 - self.winner]
            return False
        
        elif action == PokerAction.CALL:
            max_bet = max(self.state.current_bets)
            call_amount = max_bet - self.state.current_bets[self.active_player]
            actual_call = min(call_amount, self.state.stacks[self.active_player])
            self.state.stacks[self.active_player] -= actual_call
            self.state.current_bets[self.active_player] += actual_call
            self.state.total_invested[self.active_player] += actual_call
            self.state.pot += actual_call
            
            if self._is_betting_round_complete():
                return self._advance_street()
            else:
                self._next_player()
                return True
        
        elif action == PokerAction.CHECK:
            max_bet = max(self.state.current_bets)
            if self.state.current_bets[self.active_player] != max_bet:
                return False
            
            if self._is_betting_round_complete():
                return self._advance_street()
            else:
                self._next_player()
                return True
        
        elif action == PokerAction.RAISE:
            if amount == 0:
                amount = self.state.pot
            
            max_bet = max(self.state.current_bets)
            call_amount = max_bet - self.state.current_bets[self.active_player]
            total_bet = call_amount + amount
            actual_bet = min(total_bet, self.state.stacks[self.active_player])
            self.state.stacks[self.active_player] -= actual_bet
            self.state.current_bets[self.active_player] += actual_bet
            self.state.total_invested[self.active_player] += actual_bet
            self.state.pot += actual_bet
            
            self.last_raiser = self.active_player
            self._next_player()
            return True
        
        return True
    
    def _next_player(self):
        self.active_player = 1 - self.active_player
    
    def _is_betting_round_complete(self) -> bool:
        if self.state.stacks[0] == 0 or self.state.stacks[1] == 0:
            return True
        
        if self.state.current_bets[0] == self.state.current_bets[1]:
            if self.last_raiser is None:
                return True
            return self.active_player == self.last_raiser
        
        return False
    
    def _deal_hole_cards(self):
        self.state.hole_cards = [[], []]
        for _ in range(2):
            for player in range(2):
                self.state.hole_cards[player].append(self.deck.deal())
    
    def _post_blinds(self):
        sb_player = self.state.button
        bb_player = 1 - self.state.button
        sb_amount = min(self.SMALL_BLIND, self.state.stacks[sb_player])
        bb_amount = min(self.BIG_BLIND, self.state.stacks[bb_player])
        
        self.state.stacks[sb_player] -= sb_amount
        self.state.stacks[bb_player] -= bb_amount
        
        self.state.current_bets[sb_player] = sb_amount
        self.state.current_bets[bb_player] = bb_amount
        self.state.total_invested[sb_player] = sb_amount
        self.state.total_invested[bb_player] = bb_amount
        self.state.pot = sb_amount + bb_amount
        
        self.active_player = sb_player
        self.last_raiser = bb_player
    
    def _advance_street(self) -> bool:
        if self.state.street >= 3:
            self._finish_hand()
            return False
        
        self.state.street += 1
        
        if self.state.street == 1:
            self.deck.deal()
            for _ in range(3):
                self.state.community_cards.append(self.deck.deal())
        elif self.state.street == 2:
            self.deck.deal()
            self.state.community_cards.append(self.deck.deal())
        elif self.state.street == 3:
            self.deck.deal()
            self.state.community_cards.append(self.deck.deal())
        
        self.state.current_bets = [0, 0]
        self.last_raiser = None
        self.active_player = 1 - self.state.button
        
        return True
    
    def _finish_hand(self):
        self.hand_finished = True
        
        strength0, _ = self.evaluator.evaluate_hand(
            self.state.hole_cards[0], self.state.community_cards
        )
        strength1, _ = self.evaluator.evaluate_hand(
            self.state.hole_cards[1], self.state.community_cards
        )
        if strength0 > strength1:
            self.winner = 0
        elif strength1 > strength0:
            self.winner = 1
        else:
            self.winner = None
        if self.winner is not None:
            self.final_scores[self.winner] = self.state.pot - self.state.total_invested[self.winner]
            self.final_scores[1 - self.winner] = -self.state.total_invested[1 - self.winner]
        else:
            pot_split = self.state.pot // 2
            self.final_scores[0] = pot_split - self.state.total_invested[0]
            self.final_scores[1] = pot_split - self.state.total_invested[1]
    
    def complete_hand(self):
        if self.hand_finished:
            self.match_scores[0] += self.final_scores[0]
            self.match_scores[1] += self.final_scores[1]
            self.hands_played += 1
            
            self.state.stacks[0] += self.final_scores[0]
            self.state.stacks[1] += self.final_scores[1]
            
            if self.state.stacks[0] <= 0:
                self.is_finished = True
                self.match_winner = 1
            elif self.state.stacks[1] <= 0:
                self.is_finished = True 
                self.match_winner = 0
        
        return not self.is_finished


class BotRunner:
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_containers = {}
    
    async def start_bot(self, bot_id: int, bot_files_dir: str, language: str) -> str:
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
        if bot_id in self.active_containers:
            container = self.active_containers[bot_id]
            try:
                container.stop(timeout=5)
            except:
                pass
            del self.active_containers[bot_id]
    
    async def get_bot_action(self, bot_id: int, game_state: GameState, legal_actions: List[PokerAction], timeout: int = 10) -> PokerAction:
        await asyncio.sleep(0.1)
        return random.choice(legal_actions)


class MatchRunner:
    
    def __init__(self, bot_files_dir: str = "/tmp/pokerbots"):
        self.bot_files_dir = bot_files_dir
        self.bot_runner = BotRunner()
    
    async def run_match(self, db: AsyncSession, match_id: int) -> Dict[str, Any]:
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
            
            max_hands = 100
            
            detailed_log.append({
                "event": "match_start",
                "bot1_name": bot1.name,
                "bot2_name": bot2.name,
                "starting_stacks": [game.STARTING_STACK, game.STARTING_STACK],
                "max_hands": max_hands
            })
            
            while game.hands_played < max_hands and not game.is_finished:
                current_hand = game.hands_played + 1
                detailed_log.append({
                    "event": "hand_start",
                    "hand_number": current_hand,
                    "stacks_before": game.state.stacks.copy(),
                    "button_player": game.state.button,
                    "blinds_posted": {"small_blind": game.SMALL_BLIND, "big_blind": game.BIG_BLIND},
                    "hole_cards": {
                        "player_0": [str(c) for c in game.state.hole_cards[0]],
                        "player_1": [str(c) for c in game.state.hole_cards[1]]
                    },
                    "pot_after_blinds": game.state.pot
                })
                
                while not game.hand_finished:
                    active_player = game.active_player
                    bot_id = bot1.id if active_player == 0 else bot2.id
                    bot_name = bot1.name if active_player == 0 else bot2.name
                    
                    street_names = ["preflop", "flop", "turn", "river"]
                    pre_action_state = {
                        "round_num": game.state.round_num,
                        "street": game.state.street,
                        "street_name": street_names[game.state.street] if game.state.street < 4 else "showdown",
                        "stacks": game.state.stacks.copy(),
                        "pot": game.state.pot,
                        "current_bets": game.state.current_bets.copy(),
                        "community_cards": [str(c) for c in game.state.community_cards],
                        "active_player": active_player,
                        "button": game.state.button
                    }
                    
                    legal_actions = game.get_legal_actions()
                    action = await self.bot_runner.get_bot_action(bot_id, game.state, legal_actions)
                    
                    max_bet = max(game.state.current_bets)
                    call_amount = max_bet - game.state.current_bets[active_player]
                    detailed_log.append({
                        "event": "player_action",
                        "hand_number": current_hand,
                        "player": active_player,
                        "player_name": bot_name,
                        "action": action.value,
                        "legal_actions": [a.value for a in legal_actions],
                        "pre_action_state": pre_action_state,
                        "call_amount": call_amount,
                        "stack_before": game.state.stacks[active_player]
                    })

                    continues = game.apply_action(action)
                    detailed_log.append({
                        "event": "action_result", 
                        "hand_number": current_hand,
                        "player": active_player,
                        "player_name": bot_name,
                        "action": action.value,
                        "stack_after": game.state.stacks[active_player],
                        "stack_change": game.state.stacks[active_player] - pre_action_state["stacks"][active_player],
                        "pot_after": game.state.pot,
                        "current_bets_after": game.state.current_bets.copy(),
                        "community_cards": [str(c) for c in game.state.community_cards],
                        "game_continues": continues,
                        "hand_finished": game.hand_finished
                    })
                    
                    game_log.append({
                        "hand": current_hand,
                        "player": active_player,
                        "action": action.value,
                        "game_state": {
                            "round_num": game.state.round_num,
                            "button": game.state.button,
                            "street": game.state.street,
                            "pot": game.state.pot,
                            "stacks": game.state.stacks.copy(),
                            "current_bets": game.state.current_bets.copy(),
                            "community_cards": [str(c) for c in game.state.community_cards]
                        }
                    })

                winner_name = "Split Pot" if game.winner is None else (bot1.name if game.winner == 0 else bot2.name)
                detailed_log.append({
                    "event": "hand_end",
                    "hand_number": current_hand,
                    "winner": game.winner,
                    "winner_name": winner_name,
                    "final_community_cards": [str(c) for c in game.state.community_cards],
                    "hole_cards": {
                        "player_0": [str(c) for c in game.state.hole_cards[0]],
                        "player_1": [str(c) for c in game.state.hole_cards[1]]
                    },
                    "stacks_before_resolution": game.state.stacks.copy(),
                    "pot_size": game.state.pot,
                    "final_scores": game.final_scores.copy()
                })
                
                match_continues = game.complete_hand()
                if match_continues:
                    game.reset()
            
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
                "hands_played": game.hands_played
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