HOST = "127.0.0.1"
PORT = 9000

TIMEOUT   = 5        # giây đợi ACK / nhận gói
MAX_RETRY = 3
LOSS_RATE = 0.10     # xác suất drop gói mô phỏng (chỉ áp dụng cho gói DATA)

STORAGE_DIR = "DISK C"
KEYS_DIR    = "keys"

# Bảng theo dõi yêu cầu
REQUIREMENTS = [
    ("AES-CBC encryption",                "OK", "crypto_utils.aes_*"),
    ("RSA-2048 key-exchange & sign",      "OK", "crypto_utils.rsa_*"),
    ("SHA-512 integrity check",           "OK", "crypto_utils.sha512"),
    ("TCP socket transport",              "OK", "net_utils.*"),
    ("Handshake Hello/Ready",             "OK", "client.handshake, server.handle"),
    ("Packet-loss simulation",            "OK", "net_utils._send_raw"),
    ("Retry ≤3 (timeout 5 s)",            "OK", "client.upload loop"),
]
