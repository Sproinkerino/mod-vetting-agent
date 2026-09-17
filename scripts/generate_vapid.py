"""Generate a VAPID key pair for Render. Never commit the printed private value."""

import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat


def encoded(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


key = ec.generate_private_key(ec.SECP256R1())
print("VAPID_PRIVATE_KEY=" + encoded(key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())))
print("VAPID_PUBLIC_KEY=" + encoded(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)))
print("VAPID_SUBJECT=mailto:replace-with-your-email@example.com")
