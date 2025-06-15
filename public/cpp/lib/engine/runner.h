#include <iostream>
#include <memory>
#include <string>
#include <cstdlib>
#include <stdexcept>
#include <fstream>
#include <sstream>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#endif

#include "../base/base_bot.h"
#include "engine_client.h"

class Socket {
private:
#ifdef _WIN32
    SOCKET sock;
#else
    int sock;
#endif
    FILE* file;

public:
    Socket(const std::string& host, int port) {
#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            throw std::runtime_error("WSAStartup failed");
        }
#endif
        struct addrinfo hints = {}, *result = nullptr;
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;
        hints.ai_protocol = IPPROTO_TCP;

        if (getaddrinfo(host.c_str(), std::to_string(port).c_str(), &hints, &result) != 0) {
            throw std::runtime_error("getaddrinfo failed");
        }

        sock = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
#ifdef _WIN32
        if (sock == INVALID_SOCKET) {
            freeaddrinfo(result);
            WSACleanup();
            throw std::runtime_error("socket failed");
        }
#else
        if (sock == -1) {
            freeaddrinfo(result);
            throw std::runtime_error("socket failed");
        }
#endif

        if (connect(sock, result->ai_addr, (int)result->ai_addrlen) != 0) {
#ifdef _WIN32
            closesocket(sock);
            freeaddrinfo(result);
            WSACleanup();
            throw std::runtime_error("connect failed");
#else
            close(sock);
            freeaddrinfo(result);
            throw std::runtime_error("connect failed");
#endif
        }

        freeaddrinfo(result);

#ifdef _WIN32
        file = _fdopen(_open_osfhandle((intptr_t)sock, 0), "r+");
#else
        file = fdopen(sock, "r+");
#endif
        if (!file) {
#ifdef _WIN32
            closesocket(sock);
            WSACleanup();
#else
            close(sock);
#endif
            throw std::runtime_error("fdopen failed");
        }
    }

    ~Socket() {
        if (file) {
            fclose(file);
        }
#ifdef _WIN32
        WSACleanup();
#endif
    }

    FILE* getFile() {
        return file;
    }
};

namespace Runner {
    inline void runBot(BaseBot* pokerbot, const std::string& host, int port) {
        try {
            Socket sock(host, port);
            EngineClient client(*pokerbot, *sock.getFile(), std::cout);
            client.run();
        } catch (const std::exception& e) {
            std::cerr << "Error: " << e.what() << std::endl;
            std::exit(1);
        }
    }
}
