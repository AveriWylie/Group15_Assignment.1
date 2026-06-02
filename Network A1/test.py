"""
CP372 - Computer Networks, Spring 2026
Assignment 1 - Automated Test Suite - G15

Spawns the server as a subprocess and runs all suggested test scenarios
directly over TCP sockets. Results are printed with PASS/FAIL.

Usage:
  python3 test.py

"""

import socket
import subprocess
import os
import sys
import time

# Config
HOST = "127.0.0.1"
# separate port so it doesn't clash with a running server
PORT = 5373
BUFFER_SIZE = 4096
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "server.py")
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "server_files")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.txt")
# Counters
passed = 0
failed = 0
# read valid usernames dynamically so the suite works for any users.txt
with open(USERS_FILE) as _f:
    _users = [line.strip() for line in _f if line.strip()]

USER1 = _users[0]
USER2 = _users[1] if len(_users) > 1 else _users[0]
INVALID_USER = "NotAUser"

while INVALID_USER in _users:
    INVALID_USER += "X"

passed = 0
failed = 0


def send_line(sock, line):
    sock.sendall((line + "\n").encode("utf-8"))


def recv_line(sock, timeout=5):
    sock.settimeout(timeout)
    data = b""
    while True:
        ch = sock.recv(1)
        if not ch:
            raise ConnectionError("Server closed connection.")

        if ch == b"\n":
            break

        data += ch

    return data.decode("utf-8").strip()


def new_conn():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s


def check(label, response, expect_code):
    global passed, failed
    code = response.split()[0] if response else ""
    if code == expect_code:
        print(f"  [PASS] {label}")
        passed += 1

    else:
        print(f"  [FAIL] {label}")
        print(f"         Expected code '{expect_code}', got: '{response}'")
        failed += 1


def check_true(label, condition, detail=""):
    """Assert an arbitrary boolean condition (used for content integrity)."""
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1

    else:
        print(f"  [FAIL] {label}")
        if detail:
            print(f"         {detail}")

        failed += 1


def send_file(sock, name, data):
    """
    Run the full FILE handshake for `data` (bytes) under filename `name`.
    Returns the server's final response line, or the failing line if the
    handshake aborts early.
    """
    send_line(sock, f"FILE {name}")
    r = recv_line(sock)
    if not r.startswith("OK READY"):
        return r

    send_line(sock, f"SIZE {len(data)}")
    r = recv_line(sock)
    if not r.startswith("OK SEND"):
        return r

    if data:
        sock.sendall(data)

    return recv_line(sock)


def stored_bytes(name):
    """Read back what the server actually wrote to disk, or None if absent."""
    path = os.path.join(STORAGE_DIR, name)
    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return f.read()


def test_login():
    print("\n── LOGIN tests ──")
    # Valid login
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    check(f"Valid login ({USER1})", recv_line(s), "OK")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # Invalid login
    s = new_conn()
    send_line(s, f"LOGIN {INVALID_USER}")
    check(f"Invalid login ({INVALID_USER})", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # LOGIN with no username
    s = new_conn()
    send_line(s, "LOGIN")
    check("LOGIN with no username", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()


def test_msg():
    print("\n── MSG tests ──")
    # MSG before login
    s = new_conn()
    send_line(s, "MSG Hello")
    check("MSG before LOGIN", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # MSG after login
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "MSG Hello Server!")
    check("MSG after LOGIN", recv_line(s), "OK")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # Empty MSG
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "MSG")
    check("Empty MSG", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()


def test_file_transfer():
    print("\n── FILE transfer tests ──")
    # Each case: (label, filename, payload bytes). Covers text, full byte
    # range, large random data, and the zero-byte edge case. Every case
    # asserts BOTH the OK response AND byte-for-byte integrity on disk -
    # "preserve original file contents" is not proven by the response alone.
    cases = [
        ("Small text file",        "tc_small.txt",  b"Hello from test suite!\n"),
        ("Binary file (256 bytes)", "tc_bytes.bin",  bytes(range(256))),
        ("Large file (~100 KB)",   "tc_large.bin",  os.urandom(100 * 1024)),
        ("Empty (zero-byte) file", "tc_empty.txt",  b""),
    ]

    for label, name, payload in cases:
        s = new_conn()
        send_line(s, f"LOGIN {USER1}")
        recv_line(s)
        resp = send_file(s, name, payload)
        check(label + " - response", resp, "OK")
        stored = stored_bytes(name)

        check_true(label + " - content preserved", stored == payload,
            detail=f"stored {None if stored is None else len(stored)} bytes, "
                   f""f"expected {len(payload)} bytes",
        )

        send_line(s, "QUIT")
        recv_line(s)
        s.close()

    # FILE before login
    s = new_conn()
    send_line(s, "FILE test.txt")
    check("FILE before LOGIN", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()


def test_errors():
    print("\n── Error handling tests ──")
    # Unknown command
    s = new_conn()
    send_line(s, "DANCE")
    check("Unknown command", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # Empty command
    s = new_conn()
    send_line(s, "")
    check("Empty command", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # FILE with no filename
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "FILE")
    check("FILE with no filename", recv_line(s), "ERR")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    # FILE with invalid SIZE
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "FILE dummy.txt")
    r = recv_line(s)

    if r.startswith("OK READY"):
        send_line(s, "SIZE notanumber")
        check("FILE with invalid SIZE", recv_line(s), "ERR")

    else:
        check("FILE with invalid SIZE", r, "OK")

    s.close()


def test_quit():
    print("\n── QUIT tests ──")

    s = new_conn()
    send_line(s, "QUIT")
    check("QUIT without login", recv_line(s), "OK")
    s.close()

    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "QUIT")
    check("QUIT after login", recv_line(s), "OK")
    s.close()


def test_reconnect():
    print("\n── Reconnect test ──")
    # First client connects and quits
    s = new_conn()
    send_line(s, f"LOGIN {USER1}")
    recv_line(s)
    send_line(s, "QUIT")
    recv_line(s)
    s.close()
    time.sleep(0.2)
    # Second client connects right after
    s = new_conn()
    send_line(s, f"LOGIN {USER2}")
    check("Reconnect after previous client quit", recv_line(s), "OK")
    send_line(s, "QUIT")
    recv_line(s)
    s.close()


def start_server():
    env = os.environ.copy()
    env["SERVER_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return proc


def wait_for_server(retries=20, delay=0.2):
    for _ in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.close()
            return True

        except ConnectionRefusedError:
            time.sleep(delay)

    return False


# main entry for user
def main():
    global passed, failed
    print("=" * 50)
    print("  CP372 Assignment 1 – Automated Test Suite")
    print("  Group 15")
    print("=" * 50)
    print(f"\n[INFO] Starting test server on port {PORT}...")
    server_proc = start_server()

    if not wait_for_server():
        print("[ERROR] Server did not start in time. Aborting.")
        server_proc.terminate()
        sys.exit(1)

    print("[INFO] Server ready. Running tests...\n")

    try:
        test_login()
        test_msg()
        test_file_transfer()
        test_errors()
        test_quit()
        test_reconnect()

    except Exception as e:
        print(f"\n[ERROR] Unexpected test error: {e}")

    finally:
        server_proc.terminate()
        server_proc.wait()
        print(f"\n{'=' * 50}")
        print(f"  Results: {passed} passed, {failed} failed")
        print(f"{'=' * 50}\n")
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
