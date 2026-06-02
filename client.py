"""
CP372 - Computer Networks, Spring 2026
Assignment 1 - TCP Client
Group 15

Usage:
  python3 client.py [host] [port]

  Defaults: host=127.0.0.1, port=5372

Commands:
  LOGIN <username>  - Authenticate with the server
  MSG <text>        - Send a text message
  FILE <filepath>   - Transfer a local file to the server
  QUIT              - Disconnect from the server
"""

import socket
import os
import sys

# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5372
BUFFER_SIZE = 4096


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def do_login(sock: socket.socket, args: str) -> None:
    if not args:
        print("[ERROR] Usage: LOGIN <username>")
        return

    send_line(sock, f"LOGIN {args}")
    response = recv_response(sock)
    print(f"[SERVER] {response}")


def do_msg(sock: socket.socket, args: str) -> None:
    if not args:
        print("[ERROR] Usage: MSG <text>")
        return

    send_line(sock, f"MSG {args}")
    response = recv_response(sock)
    print(f"[SERVER] {response}")


"""
File transfer protocol:
  1. Send: FILE <filename>
  2. Wait for: OK READY
  3. Send: SIZE <bytes>
  4. Wait for: OK SEND
  5. Send raw binary file data
  6. Wait for: OK FILE_RECEIVED <filename>
"""
def do_file(sock: socket.socket, args: str) -> None:
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

    if response.startswith("OK FILE_RECEIVED"):
        print(f"[INFO] File '{filename}' transferred successfully.")

    else:
        print("[ERROR] File transfer may have failed.")


def do_quit(sock: socket.socket) -> None:
    send_line(sock, "QUIT")
    try:
        response = recv_response(sock)
        print(f"[SERVER] {response}")

    except ConnectionError:
        pass

    print("[INFO] Disconnected from server.")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    try:
        port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    except ValueError:
        print("[ERROR] Port must be an integer.")
        sys.exit(1)

    print(f"[INFO] Connecting to {host}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused. Is the server running on {host}:{port}?")
        sys.exit(1)

    except OSError as e:
        print(f"[ERROR] Could not connect: {e}")
        sys.exit(1)

    print(f"[INFO] Connected to {host}:{port}")
    print("[INFO] Commands: LOGIN <user>  MSG <text>  FILE <path>  QUIT\n")

    try:
        while True:
            try:
                user_input = input("> ").strip()

            except (EOFError, KeyboardInterrupt):
                print("\n[INFO] Interrupted. Disconnecting...")
                do_quit(sock)
                break

            if not user_input:
                continue

            parts = user_input.split(" ", 1)
            command = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""

            if command == "LOGIN":
                do_login(sock, args)
            elif command == "MSG":
                do_msg(sock, args)
            elif command == "FILE":
                do_file(sock, args)
            elif command == "QUIT":
                do_quit(sock)
                break
            else:
                print(f"[ERROR] Unknown command '{command}'. Valid commands: LOGIN, MSG, FILE, QUIT")

    except ConnectionError as e:
        print(f"\n[ERROR] Connection lost: {e}")

    finally:
        sock.close()


if __name__ == "__main__":
    main()
