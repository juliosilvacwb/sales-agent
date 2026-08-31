"""RSA Key Manager for generating, loading, and persisting RSA-2048 key pairs."""
import os
import logging
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


class RsaKeyManager:
    """Manages generation, storage, and retrieval of RSA-2048 asymmetric key pairs."""

    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> Tuple[str, str]:
        """Generate an RSA key pair and return both keys in PEM string format.

        Args:
            key_size: RSA key size in bits (default 2048).

        Returns:
            Tuple of (private_key_pem, public_key_pem) strings.
        """
        logger.info("Generating new RSA-%d key pair", key_size)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem

    @classmethod
    def load_or_generate(
        cls,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Load RSA keys from environment variables, filesystem, or generate and persist them.

        Resolution order:
        1. Environment variables (`RSA_PRIVATE_KEY_PEM` and `RSA_PUBLIC_KEY_PEM`)
        2. Filesystem paths (`private_key_path` and `public_key_path`)
        3. Automatic generation (persisting to files if paths are provided)

        Args:
            private_key_path: Optional filesystem path to the private key file.
            public_key_path: Optional filesystem path to the public key file.

        Returns:
            Tuple of (private_key_pem, public_key_pem) strings.
        """
        # 1. Check environment variables
        env_priv = os.getenv("RSA_PRIVATE_KEY_PEM")
        env_pub = os.getenv("RSA_PUBLIC_KEY_PEM")
        if env_priv and env_pub:
            logger.info("Loaded RSA key pair from environment variables")
            # Normalize possible escaped newlines in env vars and ensure trailing newline
            priv = env_priv.replace("\\n", "\n")
            pub = env_pub.replace("\\n", "\n")
            if not priv.endswith("\n"):
                priv += "\n"
            if not pub.endswith("\n"):
                pub += "\n"
            return priv, pub

        # 2. Check filesystem paths
        if private_key_path and public_key_path:
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                try:
                    with open(private_key_path, "r", encoding="utf-8") as f_priv:
                        priv_content = f_priv.read()
                    with open(public_key_path, "r", encoding="utf-8") as f_pub:
                        pub_content = f_pub.read()

                    if priv_content.strip() and pub_content.strip():
                        if not priv_content.endswith("\n"):
                            priv_content += "\n"
                        if not pub_content.endswith("\n"):
                            pub_content += "\n"
                        logger.info("Loaded RSA key pair from filesystem paths: %s, %s", private_key_path, public_key_path)
                        return priv_content, pub_content
                except Exception as exc:
                    logger.warning("Failed to read existing key files (%s): %s. Regenerating.", private_key_path, exc)

        # 3. Generate new key pair
        private_pem, public_pem = cls.generate_key_pair()

        # Persist to filesystem if paths provided
        if private_key_path and public_key_path:
            try:
                for path in [private_key_path, public_key_path]:
                    dir_name = os.path.dirname(path)
                    if dir_name:
                        os.makedirs(dir_name, exist_ok=True)

                with open(private_key_path, "w", encoding="utf-8") as f_priv:
                    f_priv.write(private_pem)
                with open(public_key_path, "w", encoding="utf-8") as f_pub:
                    f_pub.write(public_pem)

                logger.info("Persisted generated RSA key pair to %s and %s", private_key_path, public_key_path)
            except Exception as exc:
                logger.warning("Could not persist generated keys to disk: %s", exc)

        return private_pem, public_pem
