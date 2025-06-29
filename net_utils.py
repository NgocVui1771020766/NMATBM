
import json, random, socket, struct
import config

# Length‑prefixed framing helpers

def _send_raw(sock: socket.socket, data: bytes):
    if random.random() < config.LOSS_RATE:
        print("[SIM] Packet dropped (not sent)")
        return
    sock.sendall(struct.pack("!I", len(data)) + data)

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf

def _recv_raw(sock: socket.socket) -> bytes:
    hdr = _recv_exact(sock, 4)
    if not hdr:
        return b""
    size = struct.unpack("!I", hdr)[0]
    return _recv_exact(sock, size)

def send_json(sock: socket.socket, obj: dict):
    _send_raw(sock, json.dumps(obj).encode())

def recv_json(sock: socket.socket) -> dict:
    data = _recv_raw(sock)
    return json.loads(data.decode()) if data else {}