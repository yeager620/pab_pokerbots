use rand::Rng;
use std::collections::HashSet;

mod lib;

use lib::base::base_bot::BaseBot;
use lib::engine::engine_client::{parse_args, run_bot};
use lib::game::poker_moves::PokerMove;
use lib::game::poker_state::{GameState, RoundState, TerminalState};

struct PokerStrategy;

impl BaseBot for PokerStrategy {
    fn handle_new_round(&mut self, _game_state: &GameState, _round_state: &RoundState, _active: usize) {
        // No initialization needed for this simple strategy
    }

    fn handle_round_over(&mut self, _game_state: &GameState, terminal_state: &TerminalState, active: usize) {
        if let Some(bounty_hits) = &terminal_state.bounty_hits {
            let my_bounty_hit = bounty_hits[active];
            let bounty_rank = &terminal_state.previous_state.bounties[active];
            
            if my_bounty_hit {
                println!("Hit bounty of {}!", bounty_rank);
            }
        }
    }

    fn get_action(&mut self, _game_state: &GameState, round_state: &RoundState, active: usize) -> PokerMove {
        let legal_actions: HashSet<PokerMove> = round_state.legal_actions();
        let street = round_state.street;
        let my_cards = &round_state.hands[active];
        let board_cards = &round_state.deck[..street as usize];
        let my_pip = round_state.pips[active];
        let opp_pip = round_state.pips[1 - active];
        let my_stack = round_state.stacks[active];
        let opp_stack = round_state.stacks[1 - active];
        let continue_cost = opp_pip - my_pip;
        let my_bounty = &round_state.bounties[active];
        
        let mut rng = rand::thread_rng();
        
        // Strategy implementation
        if legal_actions.contains(&PokerMove::Raise(0)) {
            let (min_raise, max_raise) = round_state.raise_bounds();
            if rng.gen::<f64>() < 0.4 {
                return PokerMove::Raise(min_raise);
            }
        }
        
        if legal_actions.contains(&PokerMove::Check) {
            return PokerMove::Check;
        }
        
        if rng.gen::<f64>() < 0.2 {
            return PokerMove::Fold;
        }
        
        PokerMove::Call
    }
}

fn main() {
    let args = parse_args();
    run_bot(PokerStrategy, args);
}

