import base64
import time
from urllib.parse import quote_plus
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# === CONFIGURATION ===
CLOUDFRONT_DOMAIN = "domain"
OBJECT_PATH = "path"
KEY_PAIR_ID = "key"
PRIVATE_KEY_FILE = "/Users/yash.verma/private_key.pem"
EXPIRATION_TIME = int(time.time()) + 3600  # valid for 1 hour

def rsa_sign(message, private_key_path):
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA1()
    )
    return base64.urlsafe_b64encode(signature).decode('utf-8')

# Canonical resource path (no newline or expiration here)
resource_url = f"{CLOUDFRONT_DOMAIN}{OBJECT_PATH}"
signature = rsa_sign(resource_url, PRIVATE_KEY_FILE)
signed_url = (
    f"{resource_url}"
    f"?Expires={EXPIRATION_TIME}"
    f"&Signature={quote_plus(signature)}"
    f"&Key-Pair-Id={KEY_PAIR_ID}"
)

print("✅ Signed URL:")
print(signed_url)
