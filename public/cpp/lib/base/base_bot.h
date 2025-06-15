#ifndef BASE_BOT_H
#define BASE_BOT_H

#include "../game/poker_moves.h"
#include "../game/game_state.h"
#include "../game/round_state.h"
#include "../game/terminal_state.h"

class BaseBot {
public:
    virtual ~BaseBot() = default;
    virtual void handleNewRound(const GameState& gameState, const RoundState& roundState, int active) = 0;
    virtual void handleRoundOver(const GameState& gameState, const TerminalState& terminalState, int active) = 0;
    virtual PokerMove getAction(const GameState& gameState, const RoundState& roundState, int active) = 0;
};

#endif
