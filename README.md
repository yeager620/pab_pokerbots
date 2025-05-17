# Poker at Berkeley PokerBots

## Structure

- `bot_main.py`: Main bot implementation that players should modify
- `lib/`:
  - `game/`: Game state and actions
    - `poker_moves.py`: Defines poker actions (Fold, Call, Check, Raise)
    - `poker_state.py`: Game state representations and logic
  - `base/`:
    - `base_bot.py`: Base bot interface with required methods
  - `engine/`:
    - `engine_client.py`: Communication with the poker engine


  
### PokerStrategy Class

TODO: add docs

### Game State Information

- `game_state`: Overall game information (bankroll, game clock, round number)
- `round_state`: information for the current round (cards, bets, stacks)
- `active`: player index (0 or 1)

## Example Strategy

The default implementation includes a simple randomized strategy
