#ifndef GAME_STATE_H
#define GAME_STATE_H

#include <string>

class GameState {
private:
    int bankroll;
    double gameClock;
    int roundNum;

public:
    GameState(int bankroll, double gameClock, int roundNum)
        : bankroll(bankroll), gameClock(gameClock), roundNum(roundNum) {}

    int getBankroll() const {
        return bankroll;
    }

    double getGameClock() const {
        return gameClock;
    }

    int getRoundNum() const {
        return roundNum;
    }
};

#endif
