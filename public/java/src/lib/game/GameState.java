package lib.game;

public class GameState {
    private final int bankroll;
    private final double gameClock;
    private final int roundNum;

    public GameState(int bankroll, double gameClock, int roundNum) {
        this.bankroll = bankroll;
        this.gameClock = gameClock;
        this.roundNum = roundNum;
    }

    public int getBankroll() {
        return bankroll;
    }

    public double getGameClock() {
        return gameClock;
    }

    public int getRoundNum() {
        return roundNum;
    }

    @Override
    public String toString() {
        return String.format("GameState(bankroll=%d, gameClock=%f, roundNum=%d)",
                bankroll, gameClock, roundNum);
    }
}