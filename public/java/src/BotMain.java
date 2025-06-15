import lib.base.BaseBot;
import lib.engine.Runner;
import lib.game.GameConstants;
import lib.game.GameState;
import lib.game.PokerMove;
import lib.game.RoundState;
import lib.game.TerminalState;

import java.util.List;
import java.util.Random;
import java.util.Set;

public class BotMain {
    public static class PokerStrategy implements BaseBot {
        private final Random random = new Random();

        @Override
        public void handleNewRound(GameState gameState, RoundState roundState, int active) {
        }

        @Override
        public void handleRoundOver(GameState gameState, TerminalState terminalState, int active) {
            boolean[] bountyHits = terminalState.getBountyHits();
            if (bountyHits != null && bountyHits[active]) {
                String bountyRank = terminalState.getPreviousState().getBounties()[active];
                System.out.println("Hit bounty of " + bountyRank + "!");
            }
        }

        @Override
        public PokerMove getAction(GameState gameState, RoundState roundState, int active) {
            Set<PokerMove> legalActions = roundState.getLegalActions();
            int street = roundState.getStreet();
            List<String> myCards = roundState.getHands()[active];
            List<String> boardCards = roundState.getDeck().subList(0, street);
            int myPip = roundState.getPips()[active];
            int oppPip = roundState.getPips()[1 - active];
            int myStack = roundState.getStacks()[active];
            int oppStack = roundState.getStacks()[1 - active];
            int continueCost = oppPip - myPip;
            String myBounty = roundState.getBounties()[active];

            for (PokerMove action : legalActions) {
                if (action instanceof PokerMove.Raise) {
                    int[] raiseBounds = roundState.getRaiseBounds();
                    if (random.nextDouble() < 0.4) {
                        return PokerMove.raise(raiseBounds[0]);
                    }
                }
            }

            if (legalActions.contains(PokerMove.check())) {
                return PokerMove.check();
            }

            if (random.nextDouble() < 0.2) {
                return PokerMove.fold();
            }

            return PokerMove.call();
        }
    }

    public static void main(String[] args) {
        String host = "localhost";
        int port = 0;

        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("--host") && i + 1 < args.length) {
                host = args[i + 1];
                i++;
            } else {
                try {
                    port = Integer.parseInt(args[i]);
                } catch (NumberFormatException e) {
                    System.err.println("Invalid port: " + args[i]);
                    System.exit(1);
                }
            }
        }

        if (port == 0) {
            System.err.println("Port is required");
            System.exit(1);
        }

        Runner.runBot(new PokerStrategy(), host, port);
    }
}