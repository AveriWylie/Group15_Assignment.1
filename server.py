"""
CP372 - Computer Networks, Spring 2026
Assignment 1 - TCP Server
Group 15

Protocol Commands:
  LOGIN <username>  - Authenticate using users.txt
  MSG <text>        - Send a text message to the server
  FILE <filename>   - Transfer a file to the server
  QUIT              - Disconnect from the server
"""

import socket
import os
import time

# ── Configuration ──────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("SERVER_PORT", 5372))
USERS_FILE = "users.txt"
STORAGE_DIR = "server_files"
BUFFER_SIZE = 4096


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_users(path: str) -> set:
    """Load valid usernames from a file (one per line)."""
    if not os.path.exists(path):
        print(f"[WARNING] Users file '{path}' not found. No users will be allowed.")
        return set()
    with open(path, "r") as f:
        return {line.strip() for line in f if line.strip()}


def send_response(conn: socket.socket, code: str, message: str) -> None:
    """Send a protocol response: '<CODE> <message>\n'."""
    response = f"{code} {message}\n"
    conn.sendall(response.encode("utf-8"))


def recv_line(conn: socket.socket) -> str:
    """Receive data until newline; return decoded line (stripped)."""
    data = b""
    while True:
        chunk = conn.recv(1)
        if not chunk:
            raise ConnectionError("Client disconnected unexpectedly.")
        if chunk == b"\n":
            break
        data += chunk
    return data.decode("utf-8").strip()


def handle_login(conn: socket.socket, args: str, valid_users: set, state: dict) -> None:
    if not args:
        send_response(conn, "ERR", "LOGIN requires a username. Usage: LOGIN <username>")
        return
    username = args.strip()
    if username in valid_users:
        state["authenticated"] = True
        state["username"] = username
        send_response(conn, "OK", f"Welcome, {username}!")
        print(f"[AUTH] User '{username}' authenticated.")
    else:
        send_response(conn, "ERR", f"Unknown user '{username}'. Access denied.")
        print(f"[AUTH] Failed login attempt for '{username}'.")


def handle_msg(conn: socket.socket, args: str, state: dict) -> None:
    if not state["authenticated"]:
        send_response(conn, "ERR", "You must LOGIN before sending messages.")
        return
    if not args:
        send_response(conn, "ERR", "MSG requires text. Usage: MSG <text>")
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[MSG] [{timestamp}] {state['username']}: {args}")
    send_response(conn, "OK", f"Message received: {args}")


def handle_file(conn: socket.socket, args: str, state: dict) -> None:
    """
    File transfer protocol:
      1. Client sends: FILE <filename>
      2. Server responds: OK READY
      3. Client sends: SIZE <bytes>
      4. Server responds: OK SEND
      5. Client sends exactly <bytes> of raw binary data
      6. Server responds: OK FILE_RECEIVED <filename>
    """
    if not state["authenticated"]:
        send_response(conn, "ERR", "You must LOGIN before transferring files.")
        return
    if not args:
        send_response(conn, "ERR", "FILE requires a filename. Usage: FILE <filename>")
        return

    filename = os.path.basename(args.strip())  # strip any path traversal
    if not filename:
        send_response(conn, "ERR", "Invalid filename.")
        return

    # Step 1 — signal ready
    send_response(conn, "OK", "READY")

    # Step 2 — receive SIZE line
    try:
        size_line = recv_line(conn)
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        return

    if not size_line.startswith("SIZE "):
        send_response(conn, "ERR", "Expected SIZE <bytes> after FILE command.")
        return

    try:
        file_size = int(size_line[5:].strip())
    except ValueError:
        send_response(conn, "ERR", "Invalid file size.")
        return

    if file_size < 0:
        send_response(conn, "ERR", "File size cannot be negative.")
        return

    # Step 3 — signal to send data
    send_response(conn, "OK", "SEND")

    # Step 4 — receive raw bytes
    received = b""
    remaining = file_size
    try:
        while remaining > 0:
            chunk = conn.recv(min(BUFFER_SIZE, remaining))
            if not chunk:
                raise ConnectionError("Connection lost during file transfer.")
            received += chunk
            remaining -= len(chunk)
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        send_response(conn, "ERR", "File transfer interrupted.")
        return

    # Step 5 — save file
    os.makedirs(STORAGE_DIR, exist_ok=True)
    dest_path = os.path.join(STORAGE_DIR, filename)
    with open(dest_path, "wb") as f:
        f.write(received)

    print(f"[FILE] Received '{filename}' ({file_size} bytes) from {state['username']}.")
    send_response(conn, "OK", f"FILE_RECEIVED {filename}")


def handle_quit(conn: socket.socket, state: dict) -> bool:
    username = state.get("username", "unknown")
    send_response(conn, "OK", "Goodbye!")
    print(f"[DISCONNECT] {username} disconnected gracefully.")
    return True  # signal to close connection


# ── Client handler ─────────────────────────────────────────────────────────────

def handle_client(conn: socket.socket, addr: tuple, valid_users: set) -> None:
    print(f"[CONNECT] Client connected from {addr[0]}:{addr[1]}")
    state = {"authenticated": False, "username": None}

    try:
        while True:
            try:
                line = recv_line(conn)
            except ConnectionError:
                print(f"[DISCONNECT] {addr[0]}:{addr[1]} disconnected unexpectedly.")
                break

            if not line:
                send_response(conn, "ERR", "Empty command received.")
                continue

            # Parse command and arguments
            parts = line.split(" ", 1)
            command = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""

            print(f"[CMD] Received: {line}")

            if command == "LOGIN":
                handle_login(conn, args, valid_users, state)
            elif command == "MSG":
                handle_msg(conn, args, state)
            elif command == "FILE":
                handle_file(conn, args, state)
            elif command == "QUIT":
                handle_quit(conn, state)
                break
            else:
                send_response(conn, "ERR", f"Unknown command '{command}'. Valid commands: LOGIN, MSG, FILE, QUIT")

    except Exception as e:
        print(f"[ERROR] Unexpected error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[INFO] Connection with {addr[0]}:{addr[1]} closed.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    valid_users = load_users(USERS_FILE)
    print(f"[INFO] Loaded {len(valid_users)} valid user(s) from '{USERS_FILE}'.")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)
        print(f"[INFO] Server listening on {HOST}:{PORT}")
        print("[INFO] Press Ctrl+C to stop the server.\n")

        while True:
            try:
                conn, addr = server_sock.accept()
                handle_client(conn, addr, valid_users)
                print("[INFO] Waiting for next client connection...\n")
            except KeyboardInterrupt:
                print("\n[INFO] Server shutting down.")
                break
            except Exception as e:
                print(f"[ERROR] Failed to handle client: {e}")

    finally:
        server_sock.close()
        print("[INFO] Server socket closed.")


if __name__ == "__main__":
    main()
