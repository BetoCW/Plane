import hmac
import hashlib
from typing import Iterable, List


def hmac_sha256_hex(server_seed: str, client_seed: str, nonce: int) -> str:
    msg = f"{client_seed}{nonce}".encode("utf-8")
    key = server_seed.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def hash_to_uniform(hex_digest: str) -> float:
    # Use first 13 hex chars (~52 bits) for uniform [0,1)
    head = hex_digest[:13]
    num = int(head, 16)
    denom = 16 ** len(head)
    return num / denom


def crash_multiplier(server_seed: str, client_seed: str, nonce: int, house_edge: float = 0.99) -> float:
    h = hmac_sha256_hex(server_seed, client_seed, nonce)
    x = hash_to_uniform(h)
    # Avoid division by zero; clamp x
    x = min(max(x, 1e-12), 1 - 1e-12)
    R = house_edge / (1.0 - x)
    # Ensure minimum of 1.0
    return max(1.0, R)


def sequence(server_seed: str, client_seed: str, start_nonce: int, rounds: int, house_edge: float = 0.99) -> List[float]:
    out: List[float] = []
    for k in range(rounds):
        out.append(crash_multiplier(server_seed, client_seed, start_nonce + k, house_edge))
    return out
