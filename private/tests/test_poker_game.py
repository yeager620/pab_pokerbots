import pytest
from unittest.mock import patch

from ..engine.poker_game import PokerGame, PokerAction, Card


class TestPokerGame:
    """Test cases for PokerGame."""
    
    def test_poker_game_initialization(self):
        """Test poker game initialization."""
        game = PokerGame(seed=42)
        
        assert game.STARTING_STACK == 400
        assert game.SMALL_BLIND == 1
        assert game.BIG_BLIND == 2
        assert game.NUM_ROUNDS == 1000
        assert len(game.deck) == 52
    
    def test_create_deck(self):
        """Test deck creation."""
        game = PokerGame()
        deck = game._create_deck()
        
        assert len(deck) == 52
        assert len(set(deck)) == 52  # All cards unique
        
        # Check that we have all ranks and suits
        ranks = set(card.rank for card in deck)
        suits = set(card.suit for card in deck)
        
        assert ranks == set(game.RANKS)
        assert suits == set(game.SUITS)
    
    def test_start_new_round(self):
        """Test starting a new round."""
        game = PokerGame(seed=42)  # Fixed seed for reproducibility
        round_state = game.start_new_round()
        
        assert round_state.button == 0
        assert round_state.street == 0  # Preflop
        assert round_state.pips == [game.SMALL_BLIND, game.BIG_BLIND]
        assert round_state.stacks == [
            game.STARTING_STACK - game.SMALL_BLIND,
            game.STARTING_STACK - game.BIG_BLIND
        ]
        assert len(round_state.hands[0]) == 2
        assert len(round_state.hands[1]) == 2
        assert len(round_state.deck) == 5  # Community cards
        assert round_state.bounties[0] is not None
        assert round_state.bounties[1] is not None
    
    def test_get_legal_actions_preflop(self):
        """Test getting legal actions preflop."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        legal_actions = game.get_legal_actions(round_state)
        
        # First to act preflop (small blind) should be able to fold, call, or raise
        assert PokerAction.FOLD in legal_actions
        assert PokerAction.CALL in legal_actions
        assert PokerAction.RAISE in legal_actions
    
    def test_get_legal_actions_no_bet(self):
        """Test getting legal actions when there's no bet."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        # Simulate post-flop with no bets
        round_state.street = 3  # Flop
        round_state.pips = [0, 0]
        round_state.button = 1
        
        legal_actions = game.get_legal_actions(round_state)
        
        # Should be able to check, raise, or fold
        assert PokerAction.CHECK in legal_actions
        assert PokerAction.RAISE in legal_actions
        assert PokerAction.FOLD in legal_actions
    
    def test_get_raise_bounds(self):
        """Test getting raise bounds."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        min_raise, max_raise = game.get_raise_bounds(round_state)
        
        # Small blind to act, needs to call 1 and raise at least the big blind
        expected_min = round_state.pips[0] + game.BIG_BLIND
        expected_max = round_state.pips[0] + round_state.stacks[0]
        
        assert min_raise == expected_min
        assert max_raise == expected_max
    
    def test_apply_action_fold(self):
        """Test applying fold action."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        result = game.apply_action(round_state, PokerAction.FOLD)
        
        # Should return terminal state
        assert hasattr(result, 'deltas')
        assert hasattr(result, 'bounty_hits')
        assert game.is_game_over()
    
    def test_apply_action_call_preflop(self):
        """Test applying call action preflop."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        result = game.apply_action(round_state, PokerAction.CALL)
        
        # Should proceed to next action with equalized pips
        assert result.pips == [game.BIG_BLIND, game.BIG_BLIND]
        assert result.button == 1
        assert not game.is_game_over()
    
    def test_apply_action_check(self):
        """Test applying check action."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        # Set up a scenario where checking is legal
        round_state.street = 3  # Flop
        round_state.pips = [0, 0]
        round_state.button = 1
        
        result = game.apply_action(round_state, PokerAction.CHECK)
        
        # Should advance button
        assert result.button == 2
        assert not game.is_game_over()
    
    def test_apply_action_raise(self):
        """Test applying raise action."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        min_raise, max_raise = game.get_raise_bounds(round_state)
        
        result = game.apply_action(round_state, PokerAction.RAISE, min_raise)
        
        # Should update pips and stacks
        assert result.pips[0] == min_raise
        assert result.stacks[0] == game.STARTING_STACK - min_raise
        assert result.button == 1
        assert not game.is_game_over()
    
    def test_proceed_street(self):
        """Test proceeding to next street."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        # Manually call _proceed_street
        next_street = game._proceed_street(round_state)
        
        if round_state.street == 0:
            assert next_street.street == 3  # Preflop to flop
        elif round_state.street == 3:
            assert next_street.street == 4  # Flop to turn
        elif round_state.street == 4:
            assert next_street.street == 5  # Turn to river
        
        assert next_street.pips == [0, 0]  # Reset betting
        assert next_street.button == 1
    
    def test_showdown(self):
        """Test showdown."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        round_state.street = 5  # River
        
        terminal_state = game._showdown(round_state)
        
        assert hasattr(terminal_state, 'deltas')
        assert hasattr(terminal_state, 'bounty_hits')
        assert terminal_state.bounty_hits is not None
        assert len(terminal_state.bounty_hits) == 2
    
    def test_check_bounty_hits(self):
        """Test bounty hit checking."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        # Set specific bounty and cards for testing
        round_state.bounties = ['A', 'K']
        round_state.hands = [
            [Card('A', 'H'), Card('2', 'C')],  # Player 0 has Ace
            [Card('K', 'D'), Card('3', 'S')]   # Player 1 has King
        ]
        round_state.deck = [Card('Q', 'H'), Card('J', 'C'), Card('T', 'S'), Card('9', 'H'), Card('8', 'D')]
        
        bounty_hits = game._check_bounty_hits(round_state)
        
        assert bounty_hits[0] is True   # Player 0 hit Ace bounty
        assert bounty_hits[1] is True   # Player 1 hit King bounty
    
    def test_serialize_state(self):
        """Test state serialization."""
        game = PokerGame(seed=42)
        round_state = game.start_new_round()
        
        serialized = game.serialize_state(round_state, 0)
        
        assert "button" in serialized
        assert "street" in serialized
        assert "pips" in serialized
        assert "stacks" in serialized
        assert "hands" in serialized
        assert "bounties" in serialized
        assert "deck" in serialized
        assert "active_player" in serialized
        assert "legal_actions" in serialized
        
        assert serialized["active_player"] == 0
        assert isinstance(serialized["legal_actions"], list)
    
    def test_game_determinism_with_seed(self):
        """Test that games are deterministic with the same seed."""
        game1 = PokerGame(seed=42)
        game2 = PokerGame(seed=42)
        
        round1 = game1.start_new_round()
        round2 = game2.start_new_round()
        
        # Should have identical initial states
        assert round1.hands[0][0].rank == round2.hands[0][0].rank
        assert round1.hands[0][0].suit == round2.hands[0][0].suit
        assert round1.bounties == round2.bounties
        assert round1.deck[0].rank == round2.deck[0].rank
    
    def test_game_non_determinism_without_seed(self):
        """Test that games are different without fixed seed."""
        game1 = PokerGame()
        game2 = PokerGame()
        
        round1 = game1.start_new_round()
        round2 = game2.start_new_round()
        
        # Should likely have different initial states
        # (There's a small chance they could be the same, but very unlikely)
        different = (
            round1.hands[0][0].rank != round2.hands[0][0].rank or
            round1.hands[0][0].suit != round2.hands[0][0].suit or
            round1.bounties != round2.bounties
        )
        assert different
    
    def test_card_string_representation(self):
        """Test card string representation."""
        card = Card('A', 'H')
        assert str(card) == "AH"
        
        card = Card('T', 'S')
        assert str(card) == "TS"
    
    def test_full_game_simulation(self):
        """Test a complete game simulation."""
        game = PokerGame(seed=42)
        
        # Start round
        round_state = game.start_new_round()
        assert not game.is_game_over()
        
        # Player 0 (small blind) calls
        round_state = game.apply_action(round_state, PokerAction.CALL)
        assert not game.is_game_over()
        
        # Player 1 (big blind) checks
        round_state = game.apply_action(round_state, PokerAction.CHECK)
        
        # Should now be on the flop
        if not game.is_game_over():
            assert round_state.street == 3
            assert round_state.button == 1
            assert round_state.pips == [0, 0]