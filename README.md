# CP372 – Assignment 1: TCP Client-Server Application
**Group 15** | Spring 2026

## Overview
A TCP-based client-server application built with Python's `socket` library.
Supports text messaging and file transfer via a custom application-layer protocol.

---

## Requirements
- Python 3.x (standard library only; no third-party/external libraries required)

`client.py` and `server.py` import only `socket`, `os`, and `time`. Host and port
are hard-coded in the source rather than read from the command line, so `sys` is
not needed and is not imported by either program.

---

## Folder Structure
```
Network A1/
├── client.py          # TCP client
├── server.py          # TCP server
├── users.txt          # Valid usernames (one per line)
├── test.py            # Automated test module
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
The client connects to `127.0.0.1:5372`, hard-coded at the top of `client.py`
(`DEFAULT_HOST` / `DEFAULT_PORT`). It takes no command-line arguments.

---

## How It Works

### Two separate programs
The client and the server are two independent programs that you launch
yourself, each in its own terminal. They are not one program and they do not
share execution. Each runs its own single thread, so at any moment there are
two threads of execution: one inside the server process, one inside the client
process. "Single-threaded" means each program has one thread internally, not
that the two share one. Control flow never jumps from one program to the other;
the only thing that crosses between them is data (bytes) over the socket,
delivered by the operating system.

### Startup and addresses
You start each program by running it (`python3 server.py`, `python3 client.py`).
Neither takes command-line arguments; their addresses are fixed in the source and
read once at startup.

The client still needs an address because it is the side that reaches *out*: it
has to know where the server is in order to connect to it. That address is
hard-coded as `127.0.0.1:5372` (`DEFAULT_HOST` / `DEFAULT_PORT` in `client.py`),
which is all the assignment requires, since it only needs to "connect using IP
address and port number," not to make them configurable. The server takes no such
address because it does not connect anywhere, it only waits. It binds its own
fixed port (so clients know where to find it) on `0.0.0.0` (all of this machine's
network interfaces) and listens there. There is nothing for it to "choose."

### The server must be running first
A server does not switch on when a client appears. It has to already be running
and waiting before any client can connect; otherwise the client gets "connection
refused." The server is the always-on side that waits; the client is the side
that comes and goes. This is why `main()` in `server.py` runs an endless loop;
the requirements state the server must "remain active until manually terminated"
and "continue waiting for another client after a disconnect."

### `listen` vs `accept`, and why no threads are needed
`server_sock.listen(1)` is a one-time setup call that returns immediately. It
does not wait for anything; it simply puts the socket into server (passive) mode
and tells the OS to queue incoming connections. The actual waiting happens in
`server_sock.accept()`, which blocks: the thread parks on that line, using no
CPU, until the OS has a connection ready, then `accept()` returns the new
connection and execution continues to the next line. The "listening" is done by
the OS kernel, not by a busy loop in the program.

Neither loop needs you to type anything to keep running. The server loop runs on
its own: `accept()` waits for a client, `handle_client()` then runs that client's
whole session (its `recv()` calls block, waking each time the client sends a
command), and when the client quits the loop returns to `accept()` for the next
one. The client loop reads what you type at the `>` prompt and dispatches it, but
the *waiting* in both programs is driven by blocking socket calls, not by
commands.

A single thread is enough because the server only serves one client at a time.
While it is serving a client it is blocked in `recv()`, and while idle it is
blocked in `accept()`, never both at once. Multithreading would only be needed
to wait in two places simultaneously (e.g. serving one client while accepting
another), which this assignment explicitly does not require.

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
| `OK` | Command succeeded (names the command, e.g. `OK LOGIN succeeded`) |
| `ERR` | Command failed (reason included) |

### Message Format
The protocol's control lines are plain text encoded as UTF-8 and terminated by a
single newline (`\n`). A command line is the command name followed by its
arguments (`LOGIN Averi`, `MSG Hello`, `FILE report.pdf`, `SIZE 42`, or bare
`QUIT`); a response line is a code followed by a message (`OK LOGIN succeeded`,
`ERR Unknown user 'x'. Access denied.`). Both sides read a line by reading bytes
up to the first `\n`.

File contents are the one exception: they are not text and are not encoded. After
the `OK SEND` handshake the client sends the file's raw bytes and the server reads
exactly `SIZE` bytes and writes them in binary. The byte count, not a newline or
any encoding, is what delimits the payload.

The assignment asks to transfer "text or binary" files, but at this level that
distinction does not exist: a file, text or binary, is just a sequence of bytes,
and a text file is only binary that happens to be readable under some encoding.
Because the transfer never decodes the payload to text and never re-encodes it,
it copies the exact bytes through and the original contents are preserved either
way. Handling text as a special case would add nothing and could only corrupt it
(wrong encoding, newline translation). So one raw-byte path covers both, which is
why arbitrary files transfer byte-for-byte.

### Connection Termination
A client ends the session by sending `QUIT`. The server replies `OK QUIT
succeeded` and closes its side of the connection; the client prints the
confirmation and closes its socket. The server then loops back to `accept()` and
waits for the next client. Unexpected disconnects (a client vanishing without
QUIT) are detected when a socket read returns no data, and are handled by closing
the connection cleanly rather than crashing.

---

## Example Session
```
> LOGIN Averi
[SERVER] OK LOGIN succeeded

> MSG Hello, Server!
[SERVER] OK MSG succeeded

> FILE test.txt
[INFO] Sending 'test.txt' (42 bytes)...
[SERVER] OK FILE succeeded
[INFO] File 'test.txt' transferred successfully.

> QUIT
[SERVER] OK QUIT succeeded
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
The test connects to a server you start yourself, so start the server first, then
run the test in a second terminal:
```bash
# terminal 1
python3 server.py

# terminal 2
python3 test.py
```
This is a guard inside `test.py` only, not application behavior: since the test
has to drive its cases against a running server, if it finds none on
`127.0.0.1:5372` it reports that and exits instead of failing every case. It has
nothing to do with normal use, where you simply keep the server running.

### What the test module is
`test.py` is not part of the application. The client and server are the
deliverables and are completely independent of it: neither imports the test,
references it, or behaves differently because of it, and both run identically
whether a person drives the client by hand or the test does. The dependency runs
one way only. `test.py` depends on the client and server; they depend on nothing
from the test.

`test.py` hard-codes the cases. It imports `client.py` and calls the client's
real functions over a real TCP socket against the server you started, with inputs
we wrote in code instead of typed at the `>` prompt. It does not reimplement the
protocol and it does not define "correct use"; it just supplies the inputs a
correct user would, for each case we want to confirm. The files are not the cases.
`server_files/` holds whatever was actually run through the server, and
`test_payloads/` holds the source files the client reads.

Because `test.py` is not part of the application, it is not bound by the
deliverables' allowed-library list. It uses a few standard-library helpers the
client and server do not (for example `contextlib.redirect_stdout`, to capture
what the client prints so a case can be checked against it). That is fine: the
allowed-library constraint applies to the deliverables, `client.py` and
`server.py`, which import only what is permitted.

The cases are the edge cases, the ones given in the assignment plus the ones we
identified ourselves: valid and invalid logins, login-required ordering (MSG and
FILE rejected before LOGIN), empty and missing arguments, unknown commands,
graceful QUIT, reconnection after a previous client leaves, and the file-transfer
cases below.

### How file integrity is verified
The file tests check the assignment's "preserve original file contents"
requirement by comparing what was sent against what the server stored. For each
case the test does the following:

1. It builds a known payload in memory (a small text file, the full 0–255 byte
   range, ~100 KB of random bytes, and a zero-byte file) and writes a copy to a
   temporary `test_payloads/` folder. That copy exists only so the client has a
   real file on disk to open and read, exactly as it would read a file a user
   chose to send. The client never knows or cares that the test created it.
2. The client reads that file and transfers it; the server receives exactly
   `SIZE` bytes and saves them into `server_files/`.
3. The test reads the stored file back out of `server_files/` and compares it,
   byte for byte, against the original payload it still holds in memory. Equal
   means the contents were preserved; any difference (or a missing file) fails the
   case and prints the byte counts.

So the in-memory payload is the "before" (what a correct client sent) and
`server_files/` is the "after" (what the server produced), and each test asserts
that after equals before. The `test_payloads/` folder is transient staging only;
the payloads are regenerated every run (the ~100 KB case is fresh random bytes
each time), so they are not a record of anything, and `test.py` deletes the folder
on exit. The evidence of success is the live `PASS`/`FAIL` report, not any leftover
file.

---

## File Transfer Protocol Detail
1. Client sends `FILE <filename>`
2. Server responds `OK READY`
3. Client sends `SIZE <bytes>`
4. Server responds `OK SEND`
5. Client sends raw binary file data
6. Server responds `OK FILE succeeded`

Received files are saved in the `server_files/` directory.

---

## Error Handling
- Invalid commands return `ERR` with a description
- LOGIN must succeed before MSG or FILE
- Missing files are caught before transfer begins
- Unexpected disconnects are handled without crashing
