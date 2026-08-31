"""Authentication Microservice FastAPI Application."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure root directory is on python path for src module resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.domain.model.auth_models import AuthCredentials
from src.domain.exception.auth_exceptions import InvalidCredentialsError, AuthenticationError
from src.domain.service.credential_validator import CredentialValidator
from src.adapter.outbound.auth.jwt_token_adapter import JwtRs256TokenAdapter
from src.adapter.outbound.auth.rsa_key_manager import RsaKeyManager
from src.application.service.authentication_service import AuthenticationApplicationService

# Environment Configuration
AUTH_USER = os.getenv("AUTH_USER", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "changeme")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH", "keys/private_key.pem")
RSA_PUBLIC_KEY_PATH = os.getenv("RSA_PUBLIC_KEY_PATH", "keys/public_key.pem")

# Initialize RSA Key Pair
private_pem, public_pem = RsaKeyManager.load_or_generate(
    private_key_path=RSA_PRIVATE_KEY_PATH,
    public_key_path=RSA_PUBLIC_KEY_PATH,
)

# Initialize Domain and Application Services
validator = CredentialValidator()
token_adapter = JwtRs256TokenAdapter(private_key_pem=private_pem)
auth_service = AuthenticationApplicationService(
    validator=validator,
    token_signer=token_adapter,
    expected_username=AUTH_USER,
    expected_password=AUTH_PASSWORD,
    token_expiration_minutes=JWT_EXPIRATION_MINUTES,
    issuer="sales-auth-service",
)

app = FastAPI(
    title="Authentication Microservice",
    description="Dedicated Zero Trust Auth Service managing RS256 JWT token lifecycle",
    version="1.0.0",
)

# CORS configuration
raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if raw_origins == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class LoginRequest(BaseModel):
    """Schema for user login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class PublicKeyResponse(BaseModel):
    """Schema for RSA public key distribution."""
    public_key: str


class HealthResponse(BaseModel):
    """Schema for health check."""
    status: str = "ok"


@app.post("/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(request: LoginRequest) -> LoginResponse:
    """Authenticate credentials and issue RS256 JWT access token."""
    try:
        credentials = AuthCredentials(username=request.username, password=request.password)
        token_resp = auth_service.authenticate(credentials)
        return LoginResponse(
            access_token=token_resp.access_token,
            token_type=token_resp.token_type,
            expires_in=token_resp.expires_in,
        )
    except (InvalidCredentialsError, AuthenticationError):
        # Sanitized error response (BR05)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )


@app.get("/auth/public-key", response_model=PublicKeyResponse)
def get_public_key() -> PublicKeyResponse:
    """Distribute RSA Public Key in PEM format."""
    return PublicKeyResponse(public_key=public_pem)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint for container probes."""
    return HealthResponse(status="ok")
