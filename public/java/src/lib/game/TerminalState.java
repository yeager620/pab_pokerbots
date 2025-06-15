package lib.game;

import java.util.Arrays;

public class TerminalState {
    private final int[] deltas;
    private final boolean[] bountyHits;
    private final RoundState previousState;

    public TerminalState(int[] deltas, boolean[] bountyHits, RoundState previousState) {
        this.deltas = Arrays.copyOf(deltas, deltas.length);
        this.bountyHits = bountyHits != null ? Arrays.copyOf(bountyHits, bountyHits.length) : null;
        this.previousState = previousState;
    }

    public int[] getDeltas() {
        return Arrays.copyOf(deltas, deltas.length);
    }

    public boolean[] getBountyHits() {
        return bountyHits != null ? Arrays.copyOf(bountyHits, bountyHits.length) : null;
    }

    public RoundState getPreviousState() {
        return previousState;
    }

    @Override
    public String toString() {
        return String.format("TerminalState(deltas=%s, bountyHits=%s)",
                Arrays.toString(deltas), Arrays.toString(bountyHits));
    }
}