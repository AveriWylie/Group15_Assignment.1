"""
CP372 - Computer Networks, Spring 2026
Assignment 1 - Automated Test Suite
Group 15

Imports client.py and calls its functions over a real TCP socket against a
server you start yourself (`python3 server.py`). Tests run the hard-coded
cases through the real client; nothing reimplements the protocol. Results
are printed with PASS/FAIL.

Usage:
  1. In one terminal:  python3 server.py
  2. In another:       python3 test.py
"""

# imports
import socket
import os
import sys
import time
import io
from contextlib import redirect_stdout
# client.py, server.py, users.txt and server_files/ live one level up from Test/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import client

# Config - connect to a server started separately on its default port
HOST = "127.0.0.1"
PORT = 5372
STORAGE_DIR = os.path.join(ROOT, "server_files")
USERS_FILE = os.path.join(ROOT, "users.txt")
PAYLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_payloads")

# read valid usernames dynamically so the suite works for any users.txt
with open(USERS_FILE) as f:
    users = [line.strip() for line in f if line.strip()]

USER1 = users[0]
USER2 = users[1] if len(users) > 1 else users[0]
INVALID_USER = "NotAUser"
passed = 0
failed = 0


# open a real connection to the running server
def connect():
    return socket.create_connection((HOST, PORT))


# call a client function, capturing what it prints to the terminal
def run(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)

    return buf.getvalue()


def check(label, output, expected):
    global passed, failed
    if expected in output:
        print(f"  [PASS] {label}")
        passed += 1

    else:
        print(f"  [FAIL] {label}")
        print(f"         Expected to find: '{expected}'")
        print(f"         In output:\n{output.strip()}")
        failed += 1


def check_file(label, name, payload):
    global passed, failed
    path = os.path.join(STORAGE_DIR, name)
    stored = None

    if os.path.exists(path):
        with open(path, "rb") as f:
            stored = f.read()

    if stored == payload:
        print(f"  [PASS] {label}")
        passed += 1

    else:
        n = "missing" if stored is None else f"{len(stored)} bytes"
        print(f"  [FAIL] {label}")
        print(f"         Stored {n}, expected {len(payload)} bytes")
        failed += 1


# write a payload file the client can send, return its path
def make_payload(name, data):
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    path = os.path.join(PAYLOAD_DIR, name)

    with open(path, "wb") as f:
        f.write(data)

    return path


def test_login():
    print("\n── LOGIN tests ──")

    s = connect()
    out = run(client.login, s, USER1)
    check(f"Valid login ({USER1})", out, "OK LOGIN succeeded")
    run(client.quit, s)
    s.close()

    s = connect()
    out = run(client.login, s, INVALID_USER)
    check(f"Invalid login ({INVALID_USER})", out, "ERR")
    run(client.quit, s)
    s.close()

    # client validates this locally and never sends it
    s = connect()
    out = run(client.login, s, "")
    check("LOGIN with no username", out, "Usage: LOGIN")
    run(client.quit, s)
    s.close()


def test_msg():
    print("\n── MSG tests ──")

    s = connect()
    out = run(client.msg, s, "Hello")
    check("MSG before LOGIN", out, "ERR")
    run(client.quit, s)
    s.close()

    s = connect()
    run(client.login, s, USER1)
    out = run(client.msg, s, "Hello Server!")
    check("MSG after LOGIN", out, "OK MSG succeeded")
    run(client.quit, s)
    s.close()

    # empty MSG is caught client-side
    s = connect()
    run(client.login, s, USER1)
    out = run(client.msg, s, "")
    check("Empty MSG", out, "Usage: MSG")
    run(client.quit, s)
    s.close()


def test_file_transfer():
    print("\n── FILE transfer tests ──")

    cases = [
        ("Small text file",         "tc_small.txt",  b"Hello from test suite!\n"),
        ("Binary file (256 bytes)", "tc_bytes.bin",  bytes(range(256))),
        ("Large file (~100 KB)",    "tc_large.bin",  os.urandom(100 * 1024)),
        ("Empty (zero-byte) file",  "tc_empty.txt",  b""),
    ]

    for label, name, payload in cases:
        path = make_payload(name, payload)
        s = connect()
        run(client.login, s, USER1)
        out = run(client.file, s, path)
        check(label + " - response", out, "OK FILE succeeded")
        check_file(label + " - content preserved", name, payload)
        run(client.quit, s)
        s.close()

    # FILE before login (file exists, so the client actually sends it)
    path = make_payload("tc_nologin.txt", b"x")
    s = connect()
    out = run(client.file, s, path)
    check("FILE before LOGIN", out, "ERR")
    run(client.quit, s)
    s.close()

    # missing local file is caught client-side
    s = connect()
    run(client.login, s, USER1)
    out = run(client.file, s, "does_not_exist.txt")
    check("FILE with missing local file", out, "File not found")
    run(client.quit, s)
    s.close()


def test_errors():
    print("\n── Error handling tests ──")

    # unknown command is rejected by the client's dispatch
    s = connect()
    out = run(client.handle, s, "DANCE")
    check("Unknown command", out, "Unknown command")
    run(client.quit, s)
    s.close()

    # FILE with no filename is caught client-side
    s = connect()
    run(client.login, s, USER1)
    out = run(client.file, s, "")
    check("FILE with no filename", out, "Usage: FILE")
    run(client.quit, s)
    s.close()


def test_quit():
    print("\n── QUIT tests ──")

    s = connect()
    out = run(client.quit, s)
    check("QUIT without login", out, "OK QUIT succeeded")
    s.close()

    s = connect()
    run(client.login, s, USER1)
    out = run(client.quit, s)
    check("QUIT after login", out, "OK QUIT succeeded")
    s.close()


def test_reconnect():
    print("\n── Reconnect test ──")

    # first client connects and quits
    s = connect()
    run(client.login, s, USER1)
    run(client.quit, s)
    s.close()
    time.sleep(0.2)

    # second client connects right after
    s = connect()
    out = run(client.login, s, USER2)
    check("Reconnect after previous client quit", out, "OK LOGIN succeeded")
    run(client.quit, s)
    s.close()


def server_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.close()
        return True

    except ConnectionRefusedError:
        return False


def cleanup():
    if not os.path.isdir(PAYLOAD_DIR):
        return

    for fn in os.listdir(PAYLOAD_DIR):
        try:
            os.remove(os.path.join(PAYLOAD_DIR, fn))

        except OSError:
            pass

    try:
        os.rmdir(PAYLOAD_DIR)

    except OSError:
        pass


# main entry for user
def main():
    global passed, failed
    print("=" * 50)
    print("  CP372 Assignment 1 – Automated Test Suite")
    print("  Group 15")
    print("=" * 50)

    if not server_running():
        print(f"\n[ERROR] No server on {HOST}:{PORT}. Start it first: python3 server.py")
        sys.exit(1)

    print(f"\n[INFO] Server found on {HOST}:{PORT}. Running tests...\n")

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
        cleanup()
        print(f"\n{'=' * 50}")
        print(f"  Results: {passed} passed, {failed} failed")
        print(f"{'=' * 50}\n")
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
