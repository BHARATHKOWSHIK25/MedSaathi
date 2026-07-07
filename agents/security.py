"""
security.py
-------------
Security features (course concept):

1. Patient data (name, phone, medication list) is encrypted at rest using
   Fernet symmetric encryption, keyed by MEDSAATHI_ENCRYPTION_KEY.
2. Phone numbers and patient names are masked before ever being written to
   logs or console output, so a leaked log file can't leak PII.
3. An explicit consent gate must be passed before any patient record is
   created or a notification is sent - no silent data collection.
"""

import json
import os

from cryptography.fernet import Fernet


class ConsentRequiredError(Exception):
    """Raised when an operation is attempted without recorded patient/family consent."""


def mask_phone(phone: str) -> str:
    """Masks all but the last 3 digits of a phone number for safe logging."""
    if not phone or len(phone) < 4:
        return "***"
    return f"{'*' * (len(phone) - 3)}{phone[-3:]}"


def mask_name(name: str) -> str:
    """Masks a patient name to initials only, for safe logging."""
    parts = [p for p in name.split() if p]
    return " ".join(f"{p[0]}." for p in parts) if parts else "N/A"


class PatientVault:
    """Encrypts and stores patient records at rest.

    In production this would back onto a proper database; for this
    submission it demonstrates the encryption pattern using a local
    encrypted file so the concept is clearly auditable in the code.
    """

    def __init__(self, storage_path: str, encryption_key: str | None = None):
        self.storage_path = storage_path
        key = encryption_key or os.environ.get("MEDSAATHI_ENCRYPTION_KEY")
        if not key:
            # Demo-safe fallback: generate an ephemeral key so the pipeline
            # still runs without a configured .env, but real deployments
            # MUST set MEDSAATHI_ENCRYPTION_KEY explicitly.
            key = Fernet.generate_key().decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def save(self, record: dict, consent_given: bool) -> None:
        if not consent_given:
            raise ConsentRequiredError(
                "Cannot store patient data without explicit consent from the "
                "patient or their registered caregiver."
            )
        plaintext = json.dumps(record).encode("utf-8")
        ciphertext = self._fernet.encrypt(plaintext)
        with open(self.storage_path, "wb") as f:
            f.write(ciphertext)

    def load(self) -> dict | None:
        if not os.path.exists(self.storage_path):
            return None
        with open(self.storage_path, "rb") as f:
            ciphertext = f.read()
        plaintext = self._fernet.decrypt(ciphertext)
        return json.loads(plaintext)
