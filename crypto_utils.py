import os, hashlib
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding as sym_padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import config

KEY_DIR = Path(config.KEYS_DIR)
KEY_DIR.mkdir(exist_ok=True)

class CryptoUtils:
    """RSA-2048 (PKCS#1 v1.5), AES-CBC, SHA-512 helpers"""

    # ---- RSA ----
    @staticmethod
    def load_or_create_rsa(prefix: str):
        priv_path = KEY_DIR / f"{prefix}_priv.pem"
        pub_path  = KEY_DIR / f"{prefix}_pub.pem"
        if priv_path.exists() and pub_path.exists():
            priv = serialization.load_pem_private_key(priv_path.read_bytes(), None, default_backend())
            pub  = serialization.load_pem_public_key(pub_path.read_bytes(),  default_backend())
            return priv, pub
        priv = rsa.generate_private_key(65537, 2048, default_backend())
        pub  = priv.public_key()
        priv_path.write_bytes(priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
        pub_path.write_bytes(pub.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
        print(f"[KEY] RSA pair generated: {priv_path} / {pub_path}")
        return priv, pub

    @staticmethod
    def rsa_encrypt(pub, data: bytes):
        return pub.encrypt(data, asym_padding.PKCS1v15())

    @staticmethod
    def rsa_decrypt(priv, data: bytes):
        return priv.decrypt(data, asym_padding.PKCS1v15())

    @staticmethod
    def rsa_sign(priv, data: bytes):
        return priv.sign(data, asym_padding.PKCS1v15(), hashes.SHA512())

    @staticmethod
    def rsa_verify(pub, sig: bytes, data: bytes):
        try:
            pub.verify(sig, data, asym_padding.PKCS1v15(), hashes.SHA512())
            return True
        except Exception:
            return False

    # ---- AES-CBC ----
    @staticmethod
    def aes_encrypt(key: bytes, iv: bytes, data: bytes):
        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        return Cipher(algorithms.AES(key), modes.CBC(iv), default_backend()).encryptor().update(padded)

    @staticmethod
    def aes_decrypt(key: bytes, iv: bytes, data: bytes):
        dec = Cipher(algorithms.AES(key), modes.CBC(iv), default_backend()).decryptor().update(data)
        unpad = sym_padding.PKCS7(128).unpadder()
        return unpad.update(dec) + unpad.finalize()

    sha512 = staticmethod(lambda d: hashlib.sha512(d).digest())
