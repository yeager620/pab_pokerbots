package lib.engine;

import lib.base.BaseBot;

import java.io.IOException;
import java.net.Socket;

public class Runner {
    public static void runBot(BaseBot pokerbot, String host, int port) {
        try {
            Socket socket = new Socket(host, port);
            EngineClient client = new EngineClient(pokerbot, socket);
            
            try {
                client.run();
            } finally {
                client.close();
            }
        } catch (IOException e) {
            System.err.println("Could not connect to " + host + ":" + port);
            e.printStackTrace();
        }
    }
}