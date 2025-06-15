package lib.base;

import lib.game.PokerMove;
import lib.game.GameState;
import lib.game.RoundState;
import lib.game.TerminalState;

public interface BaseBot {
    void handleNewRound(GameState gameState, RoundState roundState, int active);

    void handleRoundOver(GameState gameState, TerminalState terminalState, int active);

    PokerMove getAction(GameState gameState, RoundState roundState, int active);
}