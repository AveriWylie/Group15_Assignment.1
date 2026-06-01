# CP372 – Assignment 1: TCP Client-Server Application
**Group 15** | Spring 2026

## Overview
A TCP-based client-server application built with Python's `socket` library.
Supports text messaging and file transfer via a custom application-layer protocol.

---

## Requirements
- Python 3.x (no external libraries required)

---

## Folder Structure
```
Network A1/
├── client.py          # TCP client
├── server.py          # TCP server
├── users.txt          # Valid usernames (one per line)
├── test.py            # Automated test suite
├── README.md          # This file
└── server_files/      # Directory where uploaded files are stored
```

---

## How to Run

### 1. Start the Server
```bash
python3 server.py
```
The server listens on `0.0.0.0:5372` by default.

### 2. Start the Client
```bash
python3 client.py
```
Or specify a custom host/port:
```bash
python3 client.py 127.0.0.1 5372
```

---

## Protocol Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| LOGIN | `LOGIN <username>` | Authenticate using a username from `users.txt` |
| MSG | `MSG <text>` | Send a text message to the server |
| FILE | `FILE <filepath>` | Transfer a file to the server |
| QUIT | `QUIT` | Gracefully disconnect |

### Response Codes
| Code | Meaning |
|------|---------|
| `OK` | Command succeeded |
| `ERR` | Command failed (reason included) |

---

## Example Session
```
> LOGIN Averi
[SERVER] OK Welcome, Averi!

> MSG Hello, Server!
[SERVER] OK Message received: Hello, Server!

> FILE test.txt
[INFO] Sending 'test.txt' (42 bytes)...
[SERVER] OK FILE_RECEIVED test.txt
[INFO] File 'test.txt' transferred successfully.

> QUIT
[SERVER] OK Goodbye!
[INFO] Disconnected from server.
```

---

## User Authentication (`users.txt`)
The assignment requires LOGIN to validate against *"an external file that lists
valid users."* `users.txt` is that file: one username per line. On startup the
server loads it into a set; a `LOGIN <name>` succeeds only if `<name>` is present.

- **No minimum count is specified by the assignment.** This project ships with
  the group members (Averi, Yakup, Efe) to demonstrate valid logins, rejected
  logins, and multiple distinct users in the demo.
- Authentication is username-presence only - no passwords, as the spec asks for
  identification rather than secure credentials.
- If `users.txt` is missing, the server prints a warning and starts with an empty
  user set (all logins rejected) rather than crashing.

To add or change users, edit `users.txt`:
```
Averi
Yakup
Efe
```

---

## Running the Tests
```bash
python3 test.py
```
Spawns the server on a separate port and runs all scenarios over TCP, including
byte-for-byte file-content integrity checks (text, full binary range, ~100 KB,
and zero-byte files) and error/edge cases. Reports `PASS`/`FAIL` per test.

---

## File Transfer Protocol Detail
1. Client sends `FILE <filename>`
2. Server responds `OK READY`
3. Client sends `SIZE <bytes>`
4. Server responds `OK SEND`
5. Client sends raw binary file data
6. Server responds `OK FILE_RECEIVED <filename>`

Received files are saved in the `server_files/` directory.

---

## Error Handling
- Invalid commands return `ERR` with a description
- LOGIN must succeed before MSG or FILE
- Missing files are caught before transfer begins
- Unexpected disconnects are handled without crashing
