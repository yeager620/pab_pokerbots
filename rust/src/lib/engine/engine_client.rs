use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use clap::Parser;

use crate::lib::base::base_bot::BaseBot;
use crate::lib::game::poker_moves::PokerMove;
use crate::lib::game::poker_state::{GameState, RoundState, TerminalState};
use crate::lib::game::poker_state::{STARTING_STACK, BIG_BLIND, SMALL_BLIND};

pub struct EngineClient<T: BaseBot> {
    pokerbot: T,
    stream: TcpStream,
}

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub struct Args {
    /// Host to connect to
    #[arg(long, default_value = "localhost")]
    pub host: String,

    /// Port to connect to
    pub port: u16,
}

impl<T: BaseBot> EngineClient<T> {
    pub fn new(pokerbot: T, stream: TcpStream) -> Self {
        EngineClient { pokerbot, stream }
    }

    pub fn send(&mut self, action: PokerMove) {
        let code = match action {
            PokerMove::Fold => "F".to_string(),
            PokerMove::Call => "C".to_string(),
            PokerMove::Check => "K".to_string(),
            PokerMove::Raise(amount) => format!("R{}", amount),
        };
        
        writeln!(self.stream, "{}", code).expect("Failed to write to socket");
    }

    pub fn run(&mut self) {
        let mut game_state = GameState {
            bankroll: 0,
            game_clock: 0.0,
            round_num: 1,
        };
        
        let mut round_state = None;
        let mut active = 0;
        let mut round_flag = true;
        
        let reader = BufReader::new(self.stream.try_clone().expect("Failed to clone stream"));
        
        for line in reader.lines() {
            let line = line.expect("Failed to read line");
            let packet: Vec<&str> = line.trim().split(' ').collect();
            
            if packet.is_empty() {
                continue;
            }
            
            for clause in packet {
                if clause.is_empty() {
                    continue;
                }
                
                let first_char = clause.chars().next().unwrap();
                let rest = &clause[1..];
                
                match first_char {
                    'T' => {
                        let time: f64 = rest.parse().expect("Failed to parse time");
                        game_state = GameState {
                            bankroll: game_state.bankroll,
                            game_clock: time,
                            round_num: game_state.round_num,
                        };
                    },
                    'P' => {
                        active = rest.parse::<f64>().expect("Failed to parse active") as usize;
                    },
                    'H' => {
                        let mut hands = [Vec::new(), Vec::new()];
                        hands[active] = rest.split(',').map(String::from).collect();
                        let pips = [SMALL_BLIND, BIG_BLIND];
                        let stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND];
                        
                        round_state = Some(RoundState {
                            button: 0,
                            street: 0,
                            pips,
                            stacks,
                            hands,
                            bounties: ["-1".to_string(), "-1".to_string()],
                            deck: Vec::new(),
                            previous_state: None,
                        });
                    },
                    'G' => {
                        if let Some(rs) = &mut round_state {
                            rs.bounties[active] = rest.to_string();
                            
                            if round_flag {
                                self.pokerbot.handle_new_round(&game_state, rs, active);
                                round_flag = false;
                            }
                        }
                    },
                    'F' => {
                        if let Some(rs) = &round_state {
                            if let Ok(new_rs) = rs.proceed(PokerMove::Fold) {
                                round_state = Some(new_rs);
                            }
                        }
                    },
                    'C' => {
                        if let Some(rs) = &round_state {
                            if let Ok(new_rs) = rs.proceed(PokerMove::Call) {
                                round_state = Some(new_rs);
                            }
                        }
                    },
                    'K' => {
                        if let Some(rs) = &round_state {
                            if let Ok(new_rs) = rs.proceed(PokerMove::Check) {
                                round_state = Some(new_rs);
                            }
                        }
                    },
                    'R' => {
                        if let Some(rs) = &round_state {
                            let amount: i32 = rest.parse().expect("Failed to parse raise amount");
                            if let Ok(new_rs) = rs.proceed(PokerMove::Raise(amount)) {
                                round_state = Some(new_rs);
                            }
                        }
                    },
                    'B' => {
                        if let Some(rs) = &mut round_state {
                            rs.deck = rest.split(',').map(String::from).collect();
                        }
                    },
                    'O' => {
                        if let Some(rs) = &mut round_state {
                            if let Some(prev_state) = &rs.previous_state {
                                let mut new_rs = (**prev_state).clone();
                                new_rs.hands[1 - active] = rest.split(',').map(String::from).collect();
                                
                                let terminal_state = TerminalState {
                                    deltas: [0, 0],
                                    bounty_hits: None,
                                    previous_state: Box::new(new_rs),
                                };
                                
                                // dont update round_state here because were transitioning to a terminal state
                            }
                        }
                    },
                    'D' => {
                        if let Some(rs) = &round_state {
                            let delta: i32 = rest.parse().expect("Failed to parse delta");
                            let mut deltas = [-delta, -delta];
                            deltas[active] = delta;
                            
                            game_state = GameState {
                                bankroll: game_state.bankroll + delta,
                                game_clock: game_state.game_clock,
                                round_num: game_state.round_num,
                            };
                        }
                    },
                    'Y' => {
                        if let Some(rs) = &round_state {
                            let chars: Vec<char> = rest.chars().collect();
                            let hero_hit_bounty = chars.get(0) == Some(&'1');
                            let opponent_hit_bounty = chars.get(1) == Some(&'1');
                            
                            let bounty_hits = if active == 1 {
                                [opponent_hit_bounty, hero_hit_bounty]
                            } else {
                                [hero_hit_bounty, opponent_hit_bounty]
                            };
                            
                            let terminal_state = TerminalState {
                                deltas: [0, 0], // should be set from D clause
                                bounty_hits: Some(bounty_hits),
                                previous_state: Box::new(rs.clone()),
                            };
                            
                            self.pokerbot.handle_round_over(&game_state, &terminal_state, active);
                            
                            game_state = GameState {
                                bankroll: game_state.bankroll,
                                game_clock: game_state.game_clock,
                                round_num: game_state.round_num + 1,
                            };
                            
                            round_flag = true;
                        }
                    },
                    'Q' => return,
                    _ => {}
                }
            }
            
            if round_flag {
                self.send(PokerMove::Check);
            } else if let Some(rs) = &round_state {
                assert_eq!(active, (rs.button % 2) as usize);
                let action = self.pokerbot.get_action(&game_state, rs, active);
                self.send(action);
            }
        }
    }
}

pub fn parse_args() -> Args {
    Args::parse()
}

pub fn run_bot<T: BaseBot>(pokerbot: T, args: Args) {
    match TcpStream::connect(format!("{}:{}", args.host, args.port)) {
        Ok(stream) => {
            let mut client = EngineClient::new(pokerbot, stream);
            client.run();
        },
        Err(_) => {
            eprintln!("Could not connect to {}:{}", args.host, args.port);
        }
    }
}