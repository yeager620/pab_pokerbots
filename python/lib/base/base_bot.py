class BaseBot:
    def handle_new_round(self, game_state, round_state, active):
        raise NotImplementedError('handle_new_round')

    def handle_round_over(self, game_state, terminal_state, active):
        raise NotImplementedError('handle_round_over')

    def get_action(self, game_state, round_state, active):
        raise NotImplementedError('get_action')