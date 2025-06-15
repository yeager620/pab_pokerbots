package lib.engine;

import lib.base.BaseBot;
import lib.game.GameConstants;
import lib.game.GameState;
import lib.game.PokerMove;
import lib.game.RoundState;
import lib.game.TerminalState;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class EngineClient {
    private final BaseBot pokerbot;
    private final Socket socket;
    private final BufferedReader in;
    private final PrintWriter out;

    public EngineClient(BaseBot pokerbot, Socket socket) throws IOException {
        this.pokerbot = pokerbot;
        this.socket = socket;
        this.in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
        this.out = new PrintWriter(socket.getOutputStream(), true);
    }

    public void send(PokerMove action) {
        String code;
        if (action instanceof PokerMove.Fold) {
            code = "F";
        } else if (action instanceof PokerMove.Call) {
            code = "C";
        } else if (action instanceof PokerMove.Check) {
            code = "K";
        } else if (action instanceof PokerMove.Raise) {
            code = "R" + ((PokerMove.Raise) action).getAmount();
        } else {
            throw new IllegalArgumentException("Invalid action: " + action);
        }
        out.println(code);
    }

    public void run() throws IOException {
        GameState gameState = new GameState(0, 0.0, 1);
        RoundState roundState = null;
        int active = 0;
        boolean roundFlag = true;

        String line;
        while ((line = in.readLine()) != null) {
            for (String clause : line.split(" ")) {
                if (clause.isEmpty()) {
                    continue;
                }

                char firstChar = clause.charAt(0);
                String rest = clause.substring(1);

                switch (firstChar) {
                    case 'T':
                        double time = Double.parseDouble(rest);
                        gameState = new GameState(gameState.getBankroll(), time, gameState.getRoundNum());
                        break;
                    case 'P':
                        active = Integer.parseInt(rest);
                        break;
                    case 'H':
                        List<String>[] hands = new List[2];
                        hands[0] = new ArrayList<>();
                        hands[1] = new ArrayList<>();
                        if (!rest.isEmpty()) {
                            hands[active].addAll(Arrays.asList(rest.split(",")));
                        }
                        int[] pips = {GameConstants.SMALL_BLIND, GameConstants.BIG_BLIND};
                        int[] stacks = {
                            GameConstants.STARTING_STACK - GameConstants.SMALL_BLIND,
                            GameConstants.STARTING_STACK - GameConstants.BIG_BLIND
                        };
                        String[] bounties = {"-1", "-1"};
                        roundState = new RoundState(0, 0, pips, stacks, hands, bounties, new ArrayList<>(), null);
                        break;
                    case 'G':
                        if (roundState != null) {
                            String[] bounties = roundState.getBounties();
                            bounties[active] = rest;
                            roundState = new RoundState(
                                roundState.getButton(), roundState.getStreet(),
                                roundState.getPips(), roundState.getStacks(),
                                roundState.getHands(), bounties, roundState.getDeck(),
                                roundState.getPreviousState()
                            );
                            if (roundFlag) {
                                pokerbot.handleNewRound(gameState, roundState, active);
                                roundFlag = false;
                            }
                        }
                        break;
                    case 'F':
                        if (roundState != null) {
                            roundState = (RoundState) roundState.proceed(new PokerMove.Fold());
                        }
                        break;
                    case 'C':
                        if (roundState != null) {
                            roundState = (RoundState) roundState.proceed(new PokerMove.Call());
                        }
                        break;
                    case 'K':
                        if (roundState != null) {
                            roundState = (RoundState) roundState.proceed(new PokerMove.Check());
                        }
                        break;
                    case 'R':
                        if (roundState != null) {
                            int amount = Integer.parseInt(rest);
                            roundState = (RoundState) roundState.proceed(new PokerMove.Raise(amount));
                        }
                        break;
                    case 'B':
                        if (roundState != null) {
                            List<String> deck = Arrays.asList(rest.split(","));
                            roundState = new RoundState(
                                roundState.getButton(), roundState.getStreet(),
                                roundState.getPips(), roundState.getStacks(),
                                roundState.getHands(), roundState.getBounties(), deck,
                                roundState.getPreviousState()
                            );
                        }
                        break;
                    case 'O':
                        if (roundState != null && roundState.getPreviousState() != null) {
                            RoundState previousState = roundState.getPreviousState();
                            List<String>[] hands = new List[2];
                            hands[0] = new ArrayList<>(previousState.getHands()[0]);
                            hands[1] = new ArrayList<>(previousState.getHands()[1]);
                            hands[1 - active].clear();
                            if (!rest.isEmpty()) {
                                hands[1 - active].addAll(Arrays.asList(rest.split(",")));
                            }
                            roundState = new RoundState(
                                previousState.getButton(), previousState.getStreet(),
                                previousState.getPips(), previousState.getStacks(),
                                hands, previousState.getBounties(), previousState.getDeck(),
                                previousState.getPreviousState()
                            );
                        }
                        break;
                    case 'D':
                        if (roundState != null) {
                            int delta = Integer.parseInt(rest);
                            gameState = new GameState(gameState.getBankroll() + delta,
                                                    gameState.getGameClock(), gameState.getRoundNum());
                        }
                        break;
                    case 'Y':
                        if (roundState != null) {
                            boolean[] bountyHits = {rest.charAt(0) == '1', rest.charAt(1) == '1'};
                            TerminalState terminalState = new TerminalState(new int[]{0, 0}, bountyHits, roundState);
                            pokerbot.handleRoundOver(gameState, terminalState, active);
                            gameState = new GameState(gameState.getBankroll(), gameState.getGameClock(),
                                                    gameState.getRoundNum() + 1);
                            roundFlag = true;
                        }
                        break;
                    case 'Q':
                        return;
                }
            }

            if (roundFlag) {
                send(new PokerMove.Check());
            } else if (roundState != null) {
                assert active == roundState.getButton() % 2;
                PokerMove action = pokerbot.getAction(gameState, roundState, active);
                send(action);
            }
        }
    }

    public void close() throws IOException {
        in.close();
        out.close();
        socket.close();
    }
}