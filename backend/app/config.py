"""Backend settings; relative database paths resolve from the project root."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from .services.nvidia import LIGHTNING_MODEL, SUPER_MODEL

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = 'gpt-4.1-mini-2025-04-14'
    llm_timeout_seconds: float = 8.0
    llm_provider: str = 'openai'
    nvidia_api_key: str | None = field(default=None, repr=False)
    nvidia_model: str = LIGHTNING_MODEL
    nvidia_translation_model: str = SUPER_MODEL
    translation_timeout_seconds: float = 30.0

    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "backend", "testserver")

    @property
    def llm_configured(self):
        if self.llm_provider == 'nvidia':
            return bool(self.nvidia_api_key and self.nvidia_model.strip())
        return self.llm_provider == 'openai' and bool(self.openai_api_key)

    @classmethod
    def from_env(cls):
        load_dotenv(PROJECT_ROOT / "backend" / ".env", override=False)
        path = Path(os.getenv("DATABASE_PATH", "backend/data/reviews.db")).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        origins = tuple(value.strip() for value in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000"
        ).split(",") if value.strip())
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        timeout = float(os.getenv('LLM_TIMEOUT_SECONDS','8'))
        if not 0 < timeout <= 10:
            raise ValueError('LLM_TIMEOUT_SECONDS must be between 0 and 10 seconds')
        provider = os.getenv('LLM_PROVIDER', 'openai').strip().lower()
        if provider not in ('openai', 'nvidia'):
            raise ValueError('LLM_PROVIDER must be openai or nvidia')
        translation_timeout = float(os.getenv('TRANSLATION_TIMEOUT_SECONDS', '30'))
        if not 0 < translation_timeout <= 60:
            raise ValueError('TRANSLATION_TIMEOUT_SECONDS must be between 0 and 60 seconds')
        hosts=tuple(value.strip() for value in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,backend').split(',') if value.strip())
        if not hosts or '*' in hosts:
            raise ValueError('ALLOWED_HOSTS must contain explicit hosts')
        return cls(path.resolve(), origins,
                   openai_api_key=os.getenv('OPENAI_API_KEY') or None,
                   openai_model=os.getenv('OPENAI_MODEL','gpt-4.1-mini-2025-04-14'),
                   llm_timeout_seconds=timeout,
                   llm_provider=provider,
                   nvidia_api_key=os.getenv('NVIDIA_API_KEY') or None,
                   nvidia_model=os.getenv('NVIDIA_MODEL',LIGHTNING_MODEL).strip(),
                   nvidia_translation_model=os.getenv('NVIDIA_TRANSLATION_MODEL',SUPER_MODEL).strip(),
                   translation_timeout_seconds=translation_timeout,
                   allowed_hosts=hosts)
