import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


ITERATIONS = 480_000
SALT_SIZE = 16


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_text(plain_text: str, password: str) -> dict:
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password=password, salt=salt)
    token = Fernet(key).encrypt(plain_text.encode("utf-8"))
    return {
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "token": token.decode("ascii"),
    }


def decrypt_text(token_obj: dict, password: str) -> str:
    salt = base64.urlsafe_b64decode(token_obj["salt"].encode("ascii"))
    key = _derive_key(password=password, salt=salt)
    plain = Fernet(key).decrypt(token_obj["token"].encode("ascii"))
    return plain.decode("utf-8")
