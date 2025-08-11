from lib.game.poker_moves import FoldAction, CallAction, CheckAction, RaiseAction
from lib.game.poker_state import GameState, TerminalState, RoundState
from lib.game.poker_state import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from lib.base.base_bot import BaseBot
from lib.engine.engine_client import parse_args, run_bot

import random


class PokerStrategy(BaseBot):
    def __init__(self):
        pass

    def handle_new_round(self, game_state, round_state, active):
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        my_bounty_hit = terminal_state.bounty_hits[active]
        opponent_bounty_hit = terminal_state.bounty_hits[1-active]
        bounty_rank = terminal_state.previous_state.bounties[active]
        
        if my_bounty_hit:
            print(f"Hit bounty of {bounty_rank}!")

    def get_action(self, game_state, round_state, active):
        legal_actions = round_state.legal_actions()
        street = round_state.street
        my_cards = round_state.hands[active]
        board_cards = round_state.deck[:street]
        my_pip = round_state.pips[active]
        opp_pip = round_state.pips[1-active]
        my_stack = round_state.stacks[active]
        opp_stack = round_state.stacks[1-active]
        continue_cost = opp_pip - my_pip
        my_bounty = round_state.bounties[active]
        

        if RaiseAction in legal_actions:
            min_raise, max_raise = round_state.raise_bounds()
            if random.random() < 0.4:
                return RaiseAction(min_raise)
                
        if CheckAction in legal_actions:
            return CheckAction()
            
        if random.random() < 0.2:
            return FoldAction()
            
        return CallAction()


if __name__ == '__main__':
    run_bot(PokerStrategy(), parse_args())