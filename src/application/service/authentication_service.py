"""Application service for user authentication and token issuance orchestration."""
import time
import logging
from src.domain.model.auth_models import AuthCredentials, TokenClaims, TokenResponse
from src.domain.service.credential_validator import CredentialValidator
from src.application.port.inbound.authenticate_user_use_case import AuthenticateUserUseCase
from src.application.port.outbound.token_port import TokenSignerPort

logger = logging.getLogger(__name__)


class AuthenticationApplicationService(AuthenticateUserUseCase):
    """Orchestrates credential verification and asymmetric token signing."""

    def __init__(
        self,
        validator: CredentialValidator,
        token_signer: TokenSignerPort,
        expected_username: str,
        expected_password: str,
        token_expiration_minutes: int = 60,
        issuer: str = "sales-auth-service",
    ) -> None:
        self.validator = validator
        self.token_signer = token_signer
        self.expected_username = expected_username
        self.expected_password = expected_password
        self.token_expiration_minutes = token_expiration_minutes
        self.issuer = issuer

    def authenticate(self, credentials: AuthCredentials) -> TokenResponse:
        """Validate credentials and issue an RS256 signed JWT token.

        Args:
            credentials: Login credentials provided by the client.

        Returns:
            TokenResponse containing access_token, token_type, and expires_in.

        Raises:
            InvalidCredentialsError: If credentials do not match expected values.
        """
        logger.info("Authenticating user credentials for user: %s", credentials.username)
        self.validator.validate(
            credentials=credentials,
            expected_username=self.expected_username,
            expected_password=self.expected_password,
        )

        now = int(time.time())
        exp = now + (self.token_expiration_minutes * 60)
        claims = TokenClaims(
            sub=credentials.username,
            iss=self.issuer,
            iat=now,
            exp=exp,
            roles=("user",),
        )

        token_response = self.token_signer.sign(claims)
        logger.info("Authentication successful for user: %s", credentials.username)
        return token_response
