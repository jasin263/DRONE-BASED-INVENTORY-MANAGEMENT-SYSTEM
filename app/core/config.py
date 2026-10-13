"""Configuration settings for DRIMS."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Settings:
    """Application settings loaded from environment variables."""
    
    # Server settings
    app_title: str = "DRIMS - Drone Inventory Management System"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    cors_origins: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    
    # Database settings
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "drims")
    db_user: str = os.getenv("DB_USER", "drims")
    db_password: str = os.getenv("DB_PASSWORD", "drims_password")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    # Redis settings
    redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # MinIO settings
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_root_user: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_root_password: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # Keycloak settings
    keycloak_server_url: str = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
    keycloak_realm: str = os.getenv("KEYCLOAK_REALM", "drims")
    keycloak_client_id: str = os.getenv("KEYCLOAK_CLIENT_ID", "drims-api")
    keycloak_client_secret: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "secret")
    keycloak_audience: str = os.getenv("KEYCLOAK_AUDIENCE", "drims-web")
    jwks_cache_seconds: int = int(os.getenv("JWKS_CACHE_SECONDS", "300"))
    readiness_timeout_seconds: float = float(
        os.getenv("READINESS_TIMEOUT_SECONDS", "3")
    )
    
    # Processing settings
    location_time_window_seconds: int = int(os.getenv("LOCATION_TIME_WINDOW_SECONDS", "3"))
    bin_count_confidence_threshold: float = float(os.getenv("BIN_COUNT_CONFIDENCE_THRESHOLD", "0.80"))
    reconciliation_variance_threshold: int = int(os.getenv("RECONCILIATION_VARIANCE_THRESHOLD", "10"))
    
    # Weight defaults for confidence calculation
    w1_default: float = 0.5  # avg_read_confidence
    w2_default: float = 0.3  # location_method_score
    w3_default: float = 0.2  # image_coverage_ratio
    
    # IRA threshold (share of scanned bins with outcome Match)
    ira_threshold: float = float(os.getenv("IRA_THRESHOLD", "0.80"))
    
    # Retention policies (days)
    scan_data_retention_days: int = int(os.getenv("SCAN_DATA_RETENTION_DAYS", "730"))  # 2 years
    image_retention_hot_days: int = int(os.getenv("IMAGE_RETENTION_HOT_DAYS", "90"))
    audit_log_retention_days: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "2555"))  # 7 years
    
    # Rate limiting
    ingestion_rate_limit: int = int(os.getenv("INGESTION_RATE_LIMIT", "200"))  # scans per second
    api_rate_limit: int = int(os.getenv("API_RATE_LIMIT", "100"))  # requests per minute
    
    # File size limits (bytes)
    max_payload_size: int = int(os.getenv("MAX_PAYLOAD_SIZE", "10485760"))  # 10MB
    max_image_size: int = int(os.getenv("MAX_IMAGE_SIZE", "104857600"))  # 100MB


# Singleton instance
settings = Settings()

# For FastAPI dependency injection
get_settings = lambda: settings