# client.py – Upload / Download cloud simulation
# Run: python client.py --mode upload   --file video.mp4
#      python client.py --mode download --file video.mp4

import argparse, base64, json, os, socket, sys, time
from pathlib import Path
import config, net_utils as nu
from crypto_utils import CryptoUtils
from ui_utils import print_requirement_table, StepTracker

print_requirement_table()

client_priv, client_pub = CryptoUtils.load_or_create_rsa("client")
server_priv, server_pub = CryptoUtils.load_or_create_rsa("server")

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["upload", "download"], required=True)
parser.add_argument("--file", default="video.mp4")
args = parser.parse_args()

def handshake(sock: socket.socket, tracker: StepTracker):
    tracker.next("Handshake: Hello/Ready")
    nu._send_raw(sock, b"Hello!")
    if nu._recv_raw(sock) != b"Ready!":
        nu.error("Handshake failed")
        sys.exit(1)
    nu.info("    -> OK")

def upload():
    src = Path(args.file)
    if not src.exists():
        nu.error("File not found"); return
    data = src.read_bytes()
    steps = StepTracker(6)

    steps.next("Encrypt file (AES-CBC)")
    sk = os.urandom(32)
    iv = os.urandom(16)
    cipher = CryptoUtils.aes_encrypt(sk, iv, data)

    steps.next("Sign metadata (RSA/SHA-512)")
    meta = {"name": src.name, "size": len(data), "timestamp": int(time.time())}
    meta_json = json.dumps(meta, sort_keys=True).encode()
    sig_meta  = CryptoUtils.rsa_sign(client_priv, meta_json)

    steps.next("Encrypt session key (RSA)")
    enc_sk = CryptoUtils.rsa_encrypt(server_pub, sk)

    steps.next("Connect to server")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(config.TIMEOUT)
    sock.connect((config.HOST, config.PORT))
    handshake(sock, steps)

    steps.next("Send session-key packet")
    nu.send_json(sock, {"type": "KEY", "enc_sk": base64.b64encode(enc_sk).decode()})
    if nu.recv_json(sock).get("type") != "KEY-OK":
        nu.error("Server rejected session key"); return

    steps.next("Send DATA & wait ACK")
    pkt = {
        "type":   "DATA",
        "iv":     base64.b64encode(iv).decode(),
        "cipher": base64.b64encode(cipher).decode(),
        "hash":   CryptoUtils.sha512(iv + cipher).hex(),
        "sig":    base64.b64encode(sig_meta).decode(),
        "meta":   base64.b64encode(meta_json).decode(),
    }

    for attempt in range(1, config.MAX_RETRY + 1):
        nu.info(f"   attempt {attempt}")
        nu.send_json(sock, pkt)
        try:
            if nu.recv_json(sock).get("type") == "ACK":
                steps.done("Upload")
                break
        except socket.timeout:
            nu.warn("   timeout; retry")
    else:
        nu.error("Upload failed after retries")

def download():
    steps = StepTracker(5)
    steps.next("Connect to server")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(config.TIMEOUT)
    sock.connect((config.HOST, config.PORT))
    handshake(sock, steps)

    steps.next("Send signed download request")
    req_sig = CryptoUtils.rsa_sign(client_priv, args.file.encode())
    nu.send_json(sock, {
        "type": "DOWNLOAD",
        "file": args.file,
        "sig":  base64.b64encode(req_sig).decode()
    })

    steps.next("Wait DATA packet")
    resp = nu.recv_json(sock)
    if resp.get("type") != "DATA":
        nu.error("Server refused download"); return

    steps.next("Verify hash & decrypt")
    iv     = base64.b64decode(resp["iv"])
    cipher = base64.b64decode(resp["cipher"])
    if CryptoUtils.sha512(iv + cipher).hex() != resp["hash"]:
        nu.error("Hash mismatch"); return
    sk = CryptoUtils.rsa_decrypt(client_priv, base64.b64decode(resp["enc_sk"]))
    plain = CryptoUtils.aes_decrypt(sk, iv, cipher)

    Path("downloaded_" + args.file).write_bytes(plain)
    nu.send_json(sock, {"type": "ACK"})
    steps.done("Download (saved to downloaded_" + args.file + ")")

if __name__ == "__main__":
    if args.mode == "upload":
        upload()
    else:
        download()
