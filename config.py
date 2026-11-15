import os


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "fintrack-cloud-devops-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///finance.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
    DEBUG = False
    PROMETHEUS_METRICS = os.environ.get("PROMETHEUS_METRICS", "true").lower() == "true"


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"


class ProductionConfig(Config):
    """Production cloud-native configuration."""
    DEBUG = False
    TESTING = False
    # In production, require secure secret key if provided
    SECRET_KEY = os.environ.get("SECRET_KEY", "fintrack-prod-super-secure-key-cloud-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///instance/finance.db")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
