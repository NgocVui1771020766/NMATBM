import json, random, socket, struct, sys, os, config

# ---- ANSI màu (tự tắt trên CMD cũ) ----
ANSI  = sys.platform != "win32" or "ANSICON" in os.environ or "WT_SESSION" in os.environ
GREEN = "\033[32m" if ANSI else ""
RED   = "\033[31m" if ANSI else ""
YEL   = "\033[33m" if ANSI else ""
RESET = "\033[0m"  if ANSI else ""

def info(msg):  print(GREEN + msg + RESET, flush=True)
def warn(msg):  print(YEL   + msg + RESET, flush=True)
def error(msg): print(RED   + msg + RESET, flush=True)

# ---- Length-prefixed framing (4-byte big-endian) ----
def _send_raw(sock: socket.socket, data: bytes):
    """
    Gửi dữ liệu kèm chiều dài (4 byte). Control messages "Hello!" / "Ready!"
    sẽ luôn được gửi; các gói khác có thể bị drop với xác suất LOSS_RATE
    để mô phỏng lỗi mạng.
    """
    if data not in (b"Hello!", b"Ready!") and random.random() < config.LOSS_RATE:
        warn("[SIM] Packet dropped (not sent)")
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
