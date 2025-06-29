
import json, os, socket, threading, time, base64
from pathlib import Path
import config, net_utils as nu
from crypto_utils import CryptoUtils

server_priv, server_pub = CryptoUtils.load_or_create_rsa("server")
client_priv, client_pub = CryptoUtils.load_or_create_rsa("client")

Path(config.STORAGE_DIR).mkdir(exist_ok=True)

# --- Client handler ---

def handle(conn: socket.socket):
    conn.settimeout(config.TIMEOUT)
    hello = nu._recv_raw(conn)
    if hello != b"Hello!":
        conn.close(); return
    nu._send_raw(conn, b"Ready!")
    pkt = nu.recv_json(conn)
    if pkt.get("type") == "KEY":
        upload_flow(conn, pkt)
    elif pkt.get("type") == "DOWNLOAD":
        download_flow(conn, pkt)
    conn.close()

# --- Upload logic ---

def upload_flow(conn: socket.socket, key_pkt: dict):
    enc_sk = base64.b64decode(key_pkt["enc_sk"])
    session_key = CryptoUtils.rsa_decrypt(server_priv, enc_sk)
    nu.send_json(conn, {"type": "KEY-OK"})
    try:
        data_pkt = nu.recv_json(conn)
    except socket.timeout:
        print("[TIMEOUT] no DATA"); return
    if data_pkt.get("type") != "DATA":
        return
    iv = base64.b64decode(data_pkt["iv"])
    cipher = base64.b64decode(data_pkt["cipher"])
    if CryptoUtils.sha512(iv + cipher).hex() != data_pkt["hash"]:
        nu.send_json(conn, {"type": "NACK"}); return
    meta = json.loads(base64.b64decode(data_pkt["meta"]))
    sig  = base64.b64decode(data_pkt["sig"])
    if not CryptoUtils.rsa_verify(client_pub, sig, json.dumps(meta, sort_keys=True).encode()):
        nu.send_json(conn, {"type": "NACK"}); return
    plain = CryptoUtils.aes_decrypt(session_key, iv, cipher)
    Path(config.STORAGE_DIR, meta["name"]).write_bytes(plain)
    print(f"[SAVE] {meta['name']} stored ({len(plain)} bytes)")
    nu.send_json(conn, {"type": "ACK"})

# --- Download logic ---

def download_flow(conn: socket.socket, pkt: dict):
    filename = pkt["file"]
    sig = base64.b64decode(pkt["sig"])
    if not CryptoUtils.rsa_verify(client_pub, sig, filename.encode()):
        nu.send_json(conn, {"type": "NACK", "err": "auth"}); return
    path = Path(config.STORAGE_DIR, filename)
    if not path.exists():
        nu.send_json(conn, {"type": "NACK", "err": "not_found"}); return
    plain = path.read_bytes()
    session_key = os.urandom(32); iv = os.urandom(16)
    cipher = CryptoUtils.aes_encrypt(session_key, iv, plain)
    meta = {"name": filename, "size": len(plain), "timestamp": int(time.time())}
    sig_meta = CryptoUtils.rsa_sign(server_priv, json.dumps(meta, sort_keys=True).encode())
    nu.send_json(conn, {
        "type": "DATA",
        "iv": base64.b64encode(iv).decode(),
        "cipher": base64.b64encode(cipher).decode(),
        "hash": CryptoUtils.sha512(iv + cipher).hex(),
        "sig": base64.b64encode(sig_meta).decode(),
        "meta": base64.b64encode(json.dumps(meta, sort_keys=True).encode()).decode(),
        "enc_sk": base64.b64encode(CryptoUtils.rsa_encrypt(client_pub, session_key)).decode(),
    })
    try:
        ack = nu.recv_json(conn)
        if ack.get("type") == "ACK":
            print("[OK] download acknowledged")
    except socket.timeout:
        print("[WARN] client no ACK")

# --- Entry ---
if __name__ == "__main__":
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((config.HOST, config.PORT))
    srv.listen(5)
    print(f"[SERV] listening on {config.HOST}:{config.PORT}")
    try:
        while True:
            c, _ = srv.accept(); threading.Thread(target=handle, args=(c,), daemon=True).start()
    except KeyboardInterrupt:
        srv.close()
