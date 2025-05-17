import argparse
import socket
from ..game.poker_moves import FoldAction, CallAction, CheckAction, RaiseAction
from ..game.poker_state import GameState, TerminalState, RoundState
from ..game.poker_state import STARTING_STACK, BIG_BLIND, SMALL_BLIND
from ..base.base_bot import BaseBot


class EngineClient:
    def __init__(self, pokerbot, socketfile):
        self.pokerbot = pokerbot
        self.socketfile = socketfile

    def receive(self):
        while True:
            packet = self.socketfile.readline().strip().split(' ')
            if not packet:
                break
            yield packet

    def send(self, action):
        if isinstance(action, FoldAction):
            code = 'F'
        elif isinstance(action, CallAction):
            code = 'C'
        elif isinstance(action, CheckAction):
            code = 'K'
        else:  # isinstance(action, RaiseAction)
            code = 'R' + str(action.amount)
        self.socketfile.write(code + '\n')
        self.socketfile.flush()

    def run(self):
        game_state = GameState(0, 0., 1)
        round_state = None
        active = 0
        round_flag = True
        for packet in self.receive():
            for clause in packet:
                if clause[0] == 'T':
                    game_state = GameState(game_state.bankroll, float(clause[1:]), game_state.round_num)
                elif clause[0] == 'P':
                    active = int(float(clause[1:]))
                elif clause[0] == 'H':
                    hands = [[], []]
                    hands[active] = clause[1:].split(',')
                    pips = [SMALL_BLIND, BIG_BLIND]
                    stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
                    round_state = RoundState(0, 0, pips, stacks, hands, None, [], None)
                elif clause[0] == 'G':
                    bounties = ['-1', '-1']
                    bounties[active] = clause[1:]
                    round_state = RoundState(round_state.button, round_state.street, round_state.pips,
                                             round_state.stacks,
                                             round_state.hands, bounties, round_state.deck, round_state.previous_state)
                    if round_flag:
                        self.pokerbot.handle_new_round(game_state, round_state, active)
                        round_flag = False
                elif clause[0] == 'F':
                    round_state = round_state.proceed(FoldAction())
                elif clause[0] == 'C':
                    round_state = round_state.proceed(CallAction())
                elif clause[0] == 'K':
                    round_state = round_state.proceed(CheckAction())
                elif clause[0] == 'R':
                    round_state = round_state.proceed(RaiseAction(int(float(clause[1:]))))
                elif clause[0] == 'B':
                    round_state = RoundState(round_state.button, round_state.street, round_state.pips,
                                             round_state.stacks,
                                             round_state.hands, round_state.bounties, clause[1:].split(','),
                                             round_state.previous_state)
                elif clause[0] == 'O':
                    round_state = round_state.previous_state
                    revised_hands = list(round_state.hands)
                    revised_hands[1 - active] = clause[1:].split(',')
                    round_state = RoundState(round_state.button, round_state.street, round_state.pips,
                                             round_state.stacks,
                                             revised_hands, round_state.bounties, round_state.deck,
                                             round_state.previous_state)
                    round_state = TerminalState([0, 0], None, round_state)
                elif clause[0] == 'D':
                    assert isinstance(round_state, TerminalState)
                    delta = int(float(clause[1:]))
                    deltas = [-delta, -delta]
                    deltas[active] = delta
                    round_state = TerminalState(deltas, None, round_state.previous_state)
                    game_state = GameState(game_state.bankroll + delta, game_state.game_clock, game_state.round_num)
                elif clause[0] == 'Y':
                    assert isinstance(round_state, TerminalState)
                    hero_hit_bounty, opponent_hit_bounty = (clause[1] == '1'), (clause[2] == '1')
                    if active == 1:
                        hero_hit_bounty, opponent_hit_bounty = opponent_hit_bounty, hero_hit_bounty
                    round_state = TerminalState(round_state.deltas, [hero_hit_bounty, opponent_hit_bounty],
                                                round_state.previous_state)
                    self.pokerbot.handle_round_over(game_state, round_state, active)
                    game_state = GameState(game_state.bankroll, game_state.game_clock, game_state.round_num + 1)
                    round_flag = True
                elif clause[0] == 'Q':
                    return
            if round_flag:
                self.send(CheckAction())
            else:
                assert active == round_state.button % 2
                action = self.pokerbot.get_action(game_state, round_state, active)
                self.send(action)


def parse_args():
    parser = argparse.ArgumentParser(prog='python3 bot_main.py')
    parser.add_argument('--host', type=str, default='localhost', help='Host to connect to')
    parser.add_argument('port', type=int, help='Port on host to connect to')
    return parser.parse_args()


def run_bot(pokerbot, args):
    assert isinstance(pokerbot, BaseBot)
    try:
        sock = socket.create_connection((args.host, args.port))
    except OSError:
        print('Could not connect to {}:{}'.format(args.host, args.port))
        return
    socketfile = sock.makefile('rw')
    client = EngineClient(pokerbot, socketfile)
    client.run()
    socketfile.close()
    sock.close()
