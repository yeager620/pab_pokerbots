use super::poker_moves::PokerMove;
use std::collections::HashSet;

pub const NUM_ROUNDS: i32 = 1000;
pub const STARTING_STACK: i32 = 400;
pub const BIG_BLIND: i32 = 2;
pub const SMALL_BLIND: i32 = 1;

#[derive(Debug, Clone)]
pub struct GameState {
    pub bankroll: i32,
    pub game_clock: f64,
    pub round_num: i32,
}

#[derive(Debug, Clone)]
pub struct TerminalState {
    pub deltas: [i32; 2],
    pub bounty_hits: Option<[bool; 2]>,
    pub previous_state: Box<RoundState>,
}

#[derive(Debug, Clone)]
pub struct RoundState {
    pub button: i32,
    pub street: i32,
    pub pips: [i32; 2],
    pub stacks: [i32; 2],
    pub hands: [Vec<String>; 2],
    pub bounties: [String; 2],
    pub deck: Vec<String>,
    pub previous_state: Option<Box<RoundState>>,
}

impl RoundState {
    pub fn get_bounty_hits(&self) -> [bool; 2] {
        let cards0: Vec<char> = self.hands[0].iter().chain(self.deck.iter())
            .filter_map(|card| card.chars().next())
            .collect();
        let cards1: Vec<char> = self.hands[1].iter().chain(self.deck.iter())
            .filter_map(|card| card.chars().next())
            .collect();
        
        let bounty0 = self.bounties[0].chars().next().unwrap_or('-');
        let bounty1 = self.bounties[1].chars().next().unwrap_or('-');
        
        [
            cards0.contains(&bounty0),
            cards1.contains(&bounty1)
        ]
    }

    pub fn showdown(&self) -> TerminalState {
        TerminalState {
            deltas: [0, 0],
            bounty_hits: None,
            previous_state: Box::new(self.clone()),
        }
    }

    pub fn legal_actions(&self) -> HashSet<PokerMove> {
        let active = (self.button % 2) as usize;
        let continue_cost = self.pips[1 - active] - self.pips[active];
        
        let mut actions = HashSet::new();
        
        if continue_cost == 0 {
            let bets_forbidden = self.stacks[0] == 0 || self.stacks[1] == 0;
            actions.insert(PokerMove::Check);
            actions.insert(PokerMove::Fold);
            
            if !bets_forbidden {
                actions.insert(PokerMove::Raise(0)); // amt set later
            }
        } else {
            let raises_forbidden = continue_cost == self.stacks[active] || self.stacks[1 - active] == 0;
            actions.insert(PokerMove::Fold);
            actions.insert(PokerMove::Call);
            
            if !raises_forbidden {
                actions.insert(PokerMove::Raise(0)); // Amount will be set later
            }
        }
        
        actions
    }

    pub fn raise_bounds(&self) -> (i32, i32) {
        let active = (self.button % 2) as usize;
        let continue_cost = self.pips[1 - active] - self.pips[active];
        let max_contribution = self.stacks[active].min(self.stacks[1 - active] + continue_cost);
        let min_contribution = max_contribution.min(continue_cost + continue_cost.max(BIG_BLIND));
        
        (self.pips[active] + min_contribution, self.pips[active] + max_contribution)
    }

    pub fn proceed_street(&self) -> Result<RoundState, TerminalState> {
        if self.street == 5 {
            return Err(self.showdown());
        }
        
        let new_street = if self.street == 0 { 3 } else { self.street + 1 };
        
        Ok(RoundState {
            button: 1,
            street: new_street,
            pips: [0, 0],
            stacks: self.stacks,
            hands: self.hands.clone(),
            bounties: self.bounties.clone(),
            deck: self.deck.clone(),
            previous_state: Some(Box::new(self.clone())),
        })
    }

    pub fn proceed(&self, action: PokerMove) -> Result<RoundState, TerminalState> {
        let active = (self.button % 2) as usize;
        
        match action {
            PokerMove::Fold => {
                let delta = if active == 0 {
                    self.stacks[0] - STARTING_STACK
                } else {
                    STARTING_STACK - self.stacks[1]
                };
                
                Err(TerminalState {
                    deltas: [delta, -delta],
                    bounty_hits: Some(self.get_bounty_hits()),
                    previous_state: Box::new(self.clone()),
                })
            },
            PokerMove::Call => {
                if self.button == 0 {
                    return Ok(RoundState {
                        button: 1,
                        street: 0,
                        pips: [BIG_BLIND, BIG_BLIND],
                        stacks: [STARTING_STACK - BIG_BLIND, STARTING_STACK - BIG_BLIND],
                        hands: self.hands.clone(),
                        bounties: self.bounties.clone(),
                        deck: self.deck.clone(),
                        previous_state: Some(Box::new(self.clone())),
                    });
                }
                
                let mut new_pips = self.pips;
                let mut new_stacks = self.stacks;
                let contribution = new_pips[1 - active] - new_pips[active];
                new_stacks[active] -= contribution;
                new_pips[active] += contribution;
                
                let state = RoundState {
                    button: self.button + 1,
                    street: self.street,
                    pips: new_pips,
                    stacks: new_stacks,
                    hands: self.hands.clone(),
                    bounties: self.bounties.clone(),
                    deck: self.deck.clone(),
                    previous_state: Some(Box::new(self.clone())),
                };
                
                state.proceed_street()
            },
            PokerMove::Check => {
                if (self.street == 0 && self.button > 0) || self.button > 1 {
                    return self.proceed_street();
                }
                
                Ok(RoundState {
                    button: self.button + 1,
                    street: self.street,
                    pips: self.pips,
                    stacks: self.stacks,
                    hands: self.hands.clone(),
                    bounties: self.bounties.clone(),
                    deck: self.deck.clone(),
                    previous_state: Some(Box::new(self.clone())),
                })
            },
            PokerMove::Raise(amount) => {
                let mut new_pips = self.pips;
                let mut new_stacks = self.stacks;
                let contribution = amount - new_pips[active];
                new_stacks[active] -= contribution;
                new_pips[active] += contribution;
                
                Ok(RoundState {
                    button: self.button + 1,
                    street: self.street,
                    pips: new_pips,
                    stacks: new_stacks,
                    hands: self.hands.clone(),
                    bounties: self.bounties.clone(),
                    deck: self.deck.clone(),
                    previous_state: Some(Box::new(self.clone())),
                })
            }
        }
    }
}