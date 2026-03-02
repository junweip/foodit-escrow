from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Default values are placeholders; K8s / .env will overwrite these
    AWS_REGION: str = "ap-southeast-1"
    ENV: str = "dev"

    # Stripe
    STRIPE_API_KEY: str = ""

    # Platform fee percentage (e.g. 10 = 10%)
    PLATFORM_FEE_PERCENT: int = 10

    # Currency
    CURRENCY: str = "sgd"

    class Config:
        env_file = ".env"


settings = Settings()
