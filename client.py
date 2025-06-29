# client.py
import base64, json, os, socket, sys, time
from pathlib import Path
import config, net_utils as nu
from crypto_utils import CryptoUtils

client_priv, client_pub = CryptoUtils.load_or_create_rsa("client")
server_priv, server_pub = CryptoUtils.load_or_create_rsa("server")

# --- Common helpers ---

def handshake(sock):
    nu._send_raw(sock, b"Hello!")
    if nu._recv_raw(sock) != b"Ready!":
        raise RuntimeError("handshake failed")

# --- Upload flow ---
def upload(file_path: str):
    data = Path(file_path).read_bytes()
    session_key = os.urandom(32); iv = os.urandom(16)
    cipher = CryptoUtils.aes_encrypt(session_key, iv, data)
    file_hash = CryptoUtils.sha512(iv + cipher).hex()
    meta = {"name": Path(file_path).name, "size": len(data), "timestamp": int(time.time())}
    meta_json = json.dumps(meta, sort_keys=True).encode()
    sig_meta = CryptoUtils.rsa_sign(client_priv, meta_json)
    enc_sk = CryptoUtils.rsa_encrypt(server_pub, session_key)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sock.settimeout(config.TIMEOUT)
    sock.connect((config.HOST, config.PORT)); handshake(sock)

    nu.send_json(sock, {"type": "KEY", "enc_sk": base64.b64encode(enc_sk).decode()})
    if nu.recv_json(sock).get("type") != "KEY-OK":
        print("[ERR] server rejected session key"); return
    pkt = {
        "type": "DATA","iv": base64.b64encode(iv).decode(),
        "cipher": base64.b64encode(cipher).decode(),
        "hash": file_hash,
        "sig": base64.b64encode(sig_meta).decode(),
        "meta": base64.b64encode(meta_json).decode(),
    }
    for attempt in range(1, config.MAX_RETRY+1):
        print(f"[SEND] attempt {attempt}")
        nu.send_json(sock, pkt)
        try:
            resp = nu.recv_json(sock)
        except socket.timeout:
            print("[TIMEOUT] no ACK"); continue
        if resp.get("type") == "ACK":
            print("[OK] upload success"); break
        print("[NACK] will retry")
    else:
        print("[FAIL] upload failed")

# --- Download flow ---
def download(file_name: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sock.settimeout(config.TIMEOUT)
    sock.connect((config.HOST, config.PORT)); handshake(sock)
    sig = CryptoUtils.rsa_sign(client_priv, file_name.encode())
    nu.send_json(sock, {"type": "DOWNLOAD", "file": file_name, "sig": base64.b64encode(sig).decode()})
    resp = nu.recv_json(sock)
    if resp.get("type") != "DATA":
        print("[ERR] download rejected", resp); return
    iv = base64.b64decode(resp["iv"]); cipher = base64.b64decode(resp["cipher"])
    if CryptoUtils.sha512(iv+cipher).hex() != resp["hash"]:
        print("[ERR] hash mismatch"); return
    session_key = CryptoUtils.rsa_decrypt(client_priv, base64.b64decode(resp["enc_sk"]))
    plain = CryptoUtils.aes_decrypt(session_key, iv, cipher)
    out = Path("downloaded_" + file_name); out.write_bytes(plain)
    nu.send_json(sock, {"type": "ACK"})
    print(f"[OK] downloaded to {out}")

# --- Entry point for CLI ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["upload", "download"], required=True)
    parser.add_argument("--file", default="video.mp4")
    args = parser.parse_args()

    if args.mode == "upload":
        upload(args.file)
    else:
        download(args.file)
