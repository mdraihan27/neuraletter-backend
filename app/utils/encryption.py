import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib

from app.core.config import settings


def _derive_aes_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()

def encrypt_data(plaintext: str) -> str | None:
    try:
        key = _derive_aes_key(settings.RESET_PASSWORD_SECRET_KEY)
        iv = get_random_bytes(12)  

        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())

        token = base64.urlsafe_b64encode(iv + tag + ciphertext).decode()
        return token
    except Exception as e:
        print("Encryption failed:", e)
        return None

def decrypt_data(token: str) -> str | None:
    try:
        key = _derive_aes_key(settings.RESET_PASSWORD_SECRET_KEY)
        raw = base64.urlsafe_b64decode(token.encode())

        iv = raw[:12]
        tag = raw[12:28]
        ciphertext = raw[28:]

        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)

        return plaintext.decode()
    except Exception as e:
        print("Decryption failed:", e)
        return None
