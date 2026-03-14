"""
Configuration for the sample project.
Contains intentional security issues for DevLens demonstration.
"""

import os

# --- Application settings ---
APP_NAME = "SampleShop"
APP_VERSION = "1.2.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# --- Database settings ---
# Security issue: hardcoded credentials
DATABASE_URL = "postgresql://admin:password123@localhost:5432/shopdb"
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10

# --- API keys (intentionally hardcoded for demo) ---
STRIPE_API_KEY = "sk_live_YOUR_STRIPE_KEY_HERE"
SENDGRID_API_KEY = "SG.YOUR_SENDGRID_KEY_HERE"

# --- JWT settings ---
JWT_SECRET = "your-jwt-secret-here"
JWT_EXPIRY_HOURS = 24

# --- Caching ---
CACHE_BACKEND = "redis"
CACHE_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_DEFAULT_TIMEOUT = 300

# --- Feature flags ---
FEATURES = {
    "enable_coupons": True,
    "enable_international_shipping": False,
    "enable_reviews": True,
    "beta_checkout": False,
}


def get_feature(name: str, default: bool = False) -> bool:
    """Check if a feature flag is enabled."""
    return FEATURES.get(name, default)


def get_database_url() -> str:
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL", DATABASE_URL)
