from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_PREFIX: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DATABASE_URL: str

    ADMIN_EMAIL: str | None = None

    SMTP_EMAIL: str
    SMTP_PASSWORD: str
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SENDER_NAME: str = "Neuraletter"

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    SELF_BASE_URL:str

    CORS_ALLOWED_ORIGINS: list[str]

    RESET_PASSWORD_SECRET_KEY: str

    SESSION_SECRET_KEY: str

    IS_HTTPS: bool

    MISTRAL_API_KEY: str
    SERP_API_KEY: str


    class Config:
        env_file = ".env"

settings = Settings()
