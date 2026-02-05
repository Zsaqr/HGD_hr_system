import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "hr_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "hr_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "hr_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "CHANGE_ME")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    @property
    def DATABASE_URL(self) -> str:
        # SQLite mode (no Postgres / no Docker)
        sqlite_path = os.getenv("SQLITE_PATH", "hr_local.db")
        use_sqlite = os.getenv("USE_SQLITE", "1") == "1"

        if use_sqlite:
            return f"sqlite+aiosqlite:///./{sqlite_path}"   

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
