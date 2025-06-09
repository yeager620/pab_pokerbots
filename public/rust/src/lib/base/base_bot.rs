use crate::lib::game::poker_moves::PokerMove;
use crate::lib::game::poker_state::{GameState, RoundState, TerminalState};

pub trait BaseBot {
    fn handle_new_round(&mut self, game_state: &GameState, round_state: &RoundState, active: usize);
    
    fn handle_round_over(&mut self, game_state: &GameState, terminal_state: &TerminalState, active: usize);
    
    fn get_action(&mut self, game_state: &GameState, round_state: &RoundState, active: usize) -> PokerMove;
}