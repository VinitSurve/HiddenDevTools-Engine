import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Ensure env vars are loaded early
load_dotenv(override=True)

@dataclass(frozen=True)
class InstagramConfig:
    access_token: str = field(default_factory=lambda: os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip())
    business_account_id: str = field(default_factory=lambda: os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "").strip())
    app_id: str = field(default_factory=lambda: os.getenv("META_APP_ID", "").strip())
    app_secret: str = field(default_factory=lambda: os.getenv("META_APP_SECRET", "").strip())
    facebook_page_id: str = field(default_factory=lambda: os.getenv("FACEBOOK_PAGE_ID", "").strip())
    graph_api_version: str = field(default_factory=lambda: os.getenv("META_GRAPH_API_VERSION", "v23.0").strip())
    verify_token: str = field(default_factory=lambda: os.getenv("META_VERIFY_TOKEN", "").strip())

@dataclass(frozen=True)
class SupabaseConfig:
    url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", "").strip())
    service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())
    bucket: str = "posts"

@dataclass(frozen=True)
class GoogleSheetsConfig:
    service_account_file: str = field(default_factory=lambda: os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json"))
    spreadsheet_id: str = field(default_factory=lambda: os.getenv("SPREADSHEET_ID", "1IyjUOGOoOqsiLoNiza9B9wvkeQLgXCd_tYeTFlYfEUA").strip())

@dataclass(frozen=True)
class ServicesConfig:
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    google_sheets: GoogleSheetsConfig = field(default_factory=GoogleSheetsConfig)

@dataclass(frozen=True)
class SchedulerConfig:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    processing_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("PROCESSING_TIMEOUT_SECONDS", 600)))
    worker_batch_size: int = field(default_factory=lambda: int(os.getenv("WORKER_BATCH_SIZE", 10)))

@dataclass(frozen=True)
class RetryConfig:
    max_dm_retries: int = field(default_factory=lambda: int(os.getenv("MAX_DM_RETRIES", 3)))

@dataclass(frozen=True)
class LoggingConfig:
    log_output: str = field(default_factory=lambda: os.getenv("LOG_OUTPUT", "stdout"))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "logs/pipeline.jsonl"))

@dataclass(frozen=True)
class HealthConfig:
    enabled: bool = True

@dataclass(frozen=True)
class RuntimeConfig:
    persistence_backend: str = field(default_factory=lambda: os.getenv("PERSISTENCE_BACKEND", "sqlite").lower().strip())
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    health: HealthConfig = field(default_factory=HealthConfig)

@dataclass(frozen=True)
class FeatureFlags:
    enable_rendering: bool = field(default_factory=lambda: os.getenv("ENABLE_RENDERING", "true").lower() == "true")
    enable_upload: bool = field(default_factory=lambda: os.getenv("ENABLE_UPLOAD", "true").lower() == "true")
    enable_publishing: bool = field(default_factory=lambda: os.getenv("ENABLE_PUBLISHING", "true").lower() == "true")
    enable_completion: bool = field(default_factory=lambda: os.getenv("ENABLE_COMPLETION", "true").lower() == "true")
    enable_reconciliation: bool = field(default_factory=lambda: os.getenv("ENABLE_RECONCILIATION", "true").lower() == "true")
    dry_run: bool = field(default_factory=lambda: os.getenv("DRY_RUN", "false").lower() == "true")

@dataclass(frozen=True)
class AppConfig:
    services: ServicesConfig = field(default_factory=ServicesConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    @classmethod
    def load(cls):
        return cls()

# Singleton instance to be used across the application
config = AppConfig.load()
