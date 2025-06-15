package lib.game;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class RoundState {
    private final int button;
    private final int street;
    private final int[] pips;
    private final int[] stacks;
    private final List<String>[] hands;
    private final String[] bounties;
    private final List<String> deck;
    private final RoundState previousState;

    @SuppressWarnings("unchecked")
    public RoundState(int button, int street, int[] pips, int[] stacks, List<String>[] hands, 
                      String[] bounties, List<String> deck, RoundState previousState) {
        this.button = button;
        this.street = street;
        this.pips = Arrays.copyOf(pips, pips.length);
        this.stacks = Arrays.copyOf(stacks, stacks.length);
        this.hands = Arrays.copyOf(hands, hands.length);
        this.bounties = Arrays.copyOf(bounties, bounties.length);
        this.deck = deck;
        this.previousState = previousState;
    }

    public int getButton() {
        return button;
    }

    public int getStreet() {
        return street;
    }

    public int[] getPips() {
        return Arrays.copyOf(pips, pips.length);
    }

    public int[] getStacks() {
        return Arrays.copyOf(stacks, stacks.length);
    }

    public List<String>[] getHands() {
        return Arrays.copyOf(hands, hands.length);
    }

    public String[] getBounties() {
        return Arrays.copyOf(bounties, bounties.length);
    }

    public List<String> getDeck() {
        return deck;
    }

    public RoundState getPreviousState() {
        return previousState;
    }

    public Set<Class<? extends PokerMove>> getLegalActions() {
        Set<Class<? extends PokerMove>> actions = new HashSet<>();
        int active = button % 2;
        int continueCost = pips[1 - active] - pips[active];

        if (continueCost == 0) {
            actions.add(PokerMove.Check.class);
            if (stacks[active] > 0) {
                actions.add(PokerMove.Raise.class);
            }
        } else {
            actions.add(PokerMove.Fold.class);
            if (stacks[active] >= continueCost) {
                actions.add(PokerMove.Call.class);
                if (stacks[active] > continueCost) {
                    actions.add(PokerMove.Raise.class);
                }
            }
        }

        return actions;
    }

    public int[] getRaiseBounds() {
        int active = button % 2;
        int continueCost = pips[1 - active] - pips[active];
        int maxRaise = stacks[active];
        int minRaise = Math.min(maxRaise, continueCost + Math.max(continueCost, GameConstants.BIG_BLIND));
        return new int[]{minRaise, maxRaise};
    }

    public Object proceed(PokerMove action) {
        int active = button % 2;
        int continueCost = pips[1 - active] - pips[active];

        if (action instanceof PokerMove.Fold) {
            int delta = active == 0 ? pips[0] : -pips[1];
            return new TerminalState(new int[]{-delta, delta}, null, this);
        }

        if (action instanceof PokerMove.Call) {
            if (button == 0) {
                return new RoundState(1, 0,
                        new int[]{GameConstants.BIG_BLIND, GameConstants.BIG_BLIND},
                        new int[]{GameConstants.STARTING_STACK - GameConstants.BIG_BLIND,
                                GameConstants.STARTING_STACK - GameConstants.BIG_BLIND},
                        hands, bounties, deck, this);
            }

            int[] newPips = getPips();
            int[] newStacks = getStacks();
            int contribution = newPips[1 - active] - newPips[active];
            newStacks[active] -= contribution;
            newPips[active] += contribution;

            RoundState state = new RoundState(button + 1, street, newPips, newStacks, hands, bounties, deck, this);
            return state.proceedStreet();
        }

        if (action instanceof PokerMove.Check) {
            if ((street == 0 && button > 0) || button > 1) {
                return proceedStreet();
            }

            return new RoundState(button + 1, street, pips, stacks, hands, bounties, deck, this);
        }

        if (action instanceof PokerMove.Raise) {
            int amount = ((PokerMove.Raise) action).getAmount();
            int[] newPips = getPips();
            int[] newStacks = getStacks();
            int contribution = amount - newPips[active];
            newStacks[active] -= contribution;
            newPips[active] += contribution;

            return new RoundState(button + 1, street, newPips, newStacks, hands, bounties, deck, this);
        }

        throw new IllegalArgumentException("Invalid action: " + action);
    }

    private Object proceedStreet() {
        if (street == 5) {
            return new TerminalState(new int[]{0, 0}, null, this);
        }

        int newStreet = street == 0 ? 3 : street + 1;
        return new RoundState(button + 1, newStreet, new int[]{0, 0}, stacks, hands, bounties, deck, this);
    }

    @Override
    public String toString() {
        return String.format("RoundState(button=%d, street=%d, pips=%s, stacks=%s, hands=%s, bounties=%s, deck=%s)",
                button, street, Arrays.toString(pips), Arrays.toString(stacks),
                Arrays.toString(hands), Arrays.toString(bounties), deck);
    }
}