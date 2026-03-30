"""Command-line client for the search socket server."""

import socket

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 52300
BUFFER_SIZE = 4096
ENDING_MESSAGE = "q"


def start_client():
    """Connect to the search server and forward user queries."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            print(f"[Client] Connecting to {SERVER_HOST}:{SERVER_PORT}...")
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print("[Client] Connection established.")

            server_response = client_socket.recv(BUFFER_SIZE).decode("utf-8")
            print(f"[Server] {server_response}")

            while True:
                user_input = input("[Client] Enter keyword: ")
                client_socket.sendall(user_input.encode("utf-8"))

                if user_input.lower() == ENDING_MESSAGE:
                    print("[Client] Closing connection.")
                    break

                data = client_socket.recv(BUFFER_SIZE)
                print(data.decode("utf-8"))

    except ConnectionRefusedError:
        print("[Error] Could not connect to server. Is it running?")
    except Exception as error:
        print(f"[Error] An error occurred: {error}")


if __name__ == "__main__":
    start_client()
