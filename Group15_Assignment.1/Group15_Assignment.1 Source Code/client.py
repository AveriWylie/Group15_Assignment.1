"""
CP372 - Computer Networks, Spring 2026
Assignment 1 - TCP Client
Group 15
------------------------------------------------------------------------
Usage:
  python3 client.py (seperate terminal from server).

  Connects to host=127.0.0.1, port=5372 (hard-coded below).

Commands:
  LOGIN <username>  - Authenticate with the server
  MSG <text>        - Send a text message
  FILE <filepath>   - Transfer a local file to the server
  QUIT              - Disconnect from the server
------------------------------------------------------------------------
"""

# imports
import socket
import os

# Configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5372
BUFFER_SIZE = 4096

def send_line(sock: socket.socket, line: str) -> None:
    sock.sendall((line + "\n").encode("utf-8"))


def recv_response(sock: socket.socket) -> str:
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Server closed the connection.")

        if chunk == b"\n":
            break

        data += chunk

    return data.decode("utf-8").strip()


def login(sock: socket.socket, args: str) -> None:
    if not args:
        print("[ERROR] Usage: LOGIN <username>")
        return

    send_line(sock, f"LOGIN {args}")
    response = recv_response(sock)
    print(f"[SERVER] {response}")


def msg(sock: socket.socket, args: str) -> None:
    if not args:
        print("[ERROR] Usage: MSG <text>")
        return

    send_line(sock, f"MSG {args}")
    response = recv_response(sock)
    print(f"[SERVER] {response}")

    if response.startswith("OK"):
        print(f"[INFO] Message sent: {args}")


def file(sock: socket.socket, args: str) -> None:
    if not args:
        print("[ERROR] Usage: FILE <filepath>")
        return

    filepath = args.strip()

    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: '{filepath}'")
        return

    if not os.path.isfile(filepath):
        print(f"[ERROR] '{filepath}' is not a file.")
        return

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    send_line(sock, f"FILE {filename}")
    response = recv_response(sock)

    if not response.startswith("OK READY"):
        print(f"[SERVER] {response}")
        print("[ERROR] Server not ready for file transfer.")
        return

    send_line(sock, f"SIZE {file_size}")
    response = recv_response(sock)

    if not response.startswith("OK SEND"):
        print(f"[SERVER] {response}")
        print("[ERROR] Server rejected file transfer.")
        return

    print(f"[INFO] Sending '{filename}' ({file_size} bytes)...")

    try:
        with open(filepath, "rb") as f:
            sent = 0
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break

                sock.sendall(chunk)
                sent += len(chunk)

    except Exception as e:
        print(f"[ERROR] Failed to send file: {e}")
        return

    response = recv_response(sock)
    print(f"[SERVER] {response}")

    if response.startswith("OK FILE succeeded"):
        print(f"[INFO] File '{filename}' transferred successfully.")

    else:
        print("[ERROR] File transfer may have failed.")


def quit(sock: socket.socket) -> None:
    send_line(sock, "QUIT")

    try:
        response = recv_response(sock)
        print(f"[SERVER] {response}")

    except ConnectionError:
        pass

    print("[INFO] Disconnected from server.")


# dispatch a typed command line; return False when the client should quit
def handle(sock: socket.socket, user_input: str) -> bool:
    parts = user_input.split(" ", 1)
    command = parts[0].upper()
    args = parts[1] if len(parts) > 1 else ""

    if command == "LOGIN":
        login(sock, args)

    elif command == "MSG":
        msg(sock, args)

    elif command == "FILE":
        file(sock, args)

    elif command == "QUIT":
        quit(sock)
        return False

    else:
        print(f"[ERROR] Unknown command '{command}'. Valid commands: LOGIN, MSG, FILE, QUIT")

    return True


def main():
    host = DEFAULT_HOST
    port = DEFAULT_PORT

    print(f"[INFO] Connecting to {host}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused. Is the server running on {host}:{port}?")
        return

    except OSError as e:
        print(f"[ERROR] Could not connect: {e}")
        return

    print(f"[INFO] Connected to {host}:{port}")
    print("[INFO] Commands: LOGIN <user>  MSG <text>  FILE <path>  QUIT -"
          " (Do not include <> when specifying argument)")
    print("[INFO] Ctrl+C for shortcut disconnection\n")

    # post-entry command loop to execute commands
    try:
        while True:
            try:
                user_input = input("> ").strip()

            except (EOFError, KeyboardInterrupt):
                print("\n[INFO] Interrupted. Disconnecting...")
                quit(sock)
                break

            if not user_input:
                print("[INFO] No command given.")
                continue

            if not handle(sock, user_input):
                break

    except ConnectionError as e:
        print(f"\n[ERROR] Connection lost: {e}")

    finally:
        sock.close()


if __name__ == "__main__":
    main()
