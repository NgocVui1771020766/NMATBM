# server.py – Cloud simulation server
# Run: python server.py
import base64, json, os, socket, threading, time
from pathlib import Path
import config, net_utils as nu
from crypto_utils import CryptoUtils
from ui_utils import print_requirement_table

print_requirement_table()

# --- Khởi tạo khóa & thư mục lưu trữ ---
server_priv, server_pub = CryptoUtils.load_or_create_rsa("server")
client_priv, client_pub = CryptoUtils.load_or_create_rsa("client")
Path(config.STORAGE_DIR).mkdir(exist_ok=True)

# --- Hàm xử lý mỗi kết nối ---
def handle(conn: socket.socket):
    conn.settimeout(config.TIMEOUT)
    try:
        # Handshake
        if nu._recv_raw(conn) != b"Hello!":
            conn.close(); return
        nu._send_raw(conn, b"Ready!")

        pkt = nu.recv_json(conn)
        if pkt.get("type") == "KEY":
            upload_flow(conn, pkt)
        elif pkt.get("type") == "DOWNLOAD":
            download_flow(conn, pkt)
    except Exception as e:
        nu.warn(f"[EX] {e}")
    finally:
        conn.close()

# --- Upload flow ---
def upload_flow(conn, key_pkt):
    try:
        sk = CryptoUtils.rsa_decrypt(server_priv,
                                     base64.b64decode(key_pkt["enc_sk"]))
    except Exception:
        nu.send_json(conn, {"type": "NACK"}); return

    nu.send_json(conn, {"type": "KEY-OK"})

    # Mở rộng cửa sổ chờ (reties)
    conn.settimeout(config.TIMEOUT * (config.MAX_RETRY + 1))
    try:
        data_pkt = nu.recv_json(conn)
    except socket.timeout:
        nu.warn("[TIMEOUT] No DATA received"); return
    if data_pkt.get("type") != "DATA":
        return

    iv     = base64.b64decode(data_pkt["iv"])
    cipher = base64.b64decode(data_pkt["cipher"])
    if CryptoUtils.sha512(iv + cipher).hex() != data_pkt["hash"]:
        nu.send_json(conn, {"type": "NACK"}); return

    if not CryptoUtils.rsa_verify(client_pub,
                                  base64.b64decode(data_pkt["sig"]),
                                  base64.b64decode(data_pkt["meta"])):
        nu.send_json(conn, {"type": "NACK"}); return

    meta = json.loads(base64.b64decode(data_pkt["meta"]))
    plain = CryptoUtils.aes_decrypt(sk, iv, cipher)
    Path(config.STORAGE_DIR, meta["name"]).write_bytes(plain)
    nu.info(f"[SAVE] {meta['name']} stored ({len(plain)} bytes)")
    nu.send_json(conn, {"type": "ACK"})

# --- Download flow ---
def download_flow(conn, pkt):
    filename = pkt["file"]
    if not CryptoUtils.rsa_verify(client_pub,
                                  base64.b64decode(pkt["sig"]),
                                  filename.encode()):
        nu.send_json(conn, {"type": "NACK", "err": "auth"}); return

    path = Path(config.STORAGE_DIR, filename)
    if not path.exists():
        nu.send_json(conn, {"type": "NACK", "err": "not_found"}); return

    plain = path.read_bytes()
    sk  = os.urandom(32)
    iv  = os.urandom(16)
    cipher = CryptoUtils.aes_encrypt(sk, iv, plain)
    meta = {"name": filename, "size": len(plain), "timestamp": int(time.time())}
    sig_meta = CryptoUtils.rsa_sign(server_priv,
                                    json.dumps(meta, sort_keys=True).encode())

    nu.send_json(conn, {
        "type":   "DATA",
        "iv":     base64.b64encode(iv).decode(),
        "cipher": base64.b64encode(cipher).decode(),
        "hash":   CryptoUtils.sha512(iv + cipher).hex(),
        "sig":    base64.b64encode(sig_meta).decode(),
        "meta":   base64.b64encode(json.dumps(meta, sort_keys=True).encode()).decode(),
        "enc_sk": base64.b64encode(CryptoUtils.rsa_encrypt(client_pub, sk)).decode(),
    })

    conn.settimeout(config.TIMEOUT)
    try:
        if nu.recv_json(conn).get("type") == "ACK":
            nu.info("[OK] Download acknowledged")
    except socket.timeout:
        nu.warn("[WARN] Client did not ACK")

# --- Main loop ---
if __name__ == "__main__":
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((config.HOST, config.PORT))
    srv.listen(5)
    nu.info(f"[SERV] Listening on {config.HOST}:{config.PORT}")
    try:
        while True:
            c, addr = srv.accept(); nu.info(f"[SERV] Connection from {addr}")
            threading.Thread(target=handle, args=(c,), daemon=True).start()
    except KeyboardInterrupt:
        nu.info("[SERV] Shutdown"); srv.close()
