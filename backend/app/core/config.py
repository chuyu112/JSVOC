from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DEV_AUTH_SECRET = "jsvoc-dev-secret"


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./jsvoc_dev.db", alias="DATABASE_URL")
    api_cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,https://JSVOC.jadejinyuxuan.com",
        alias="API_CORS_ORIGINS",
    )
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="mock-model", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=180.0, alias="LLM_TIMEOUT_SECONDS", gt=0)
    llm_max_tokens_default: int = Field(default=8000, alias="LLM_MAX_TOKENS_DEFAULT", gt=0, le=128000)
    web_search_base_url: str = Field(default="", alias="WEB_SEARCH_BASE_URL")
    web_search_api_key: str = Field(default="", alias="WEB_SEARCH_API_KEY")
    web_search_model: str = Field(default="", alias="WEB_SEARCH_MODEL")
    web_search_context_size: str = Field(default="medium", alias="WEB_SEARCH_CONTEXT_SIZE")
    hot_video_search_provider: str = Field(default="auto", alias="HOT_VIDEO_SEARCH_PROVIDER")
    opencli_hot_video_search_command: str = Field(default="", alias="OPENCLI_HOT_VIDEO_SEARCH_COMMAND")
    opencli_search_timeout_seconds: float = Field(default=30.0, alias="OPENCLI_SEARCH_TIMEOUT_SECONDS", gt=0)
    environment: str = Field(default="development", alias="APP_ENV")
    auth_secret_key: str = Field(default=DEFAULT_DEV_AUTH_SECRET, alias="AUTH_SECRET_KEY")
    auth_cookie_name: str = Field(default="jsvoc_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")
    auth_session_ttl_seconds: int = Field(default=604800, alias="AUTH_SESSION_TTL_SECONDS", gt=0)
    admin_usernames: str = Field(default="chuyu111", alias="ADMIN_USERNAMES")
    oss_access_key_id: str = Field(default="", alias="OSS_ACCESS_KEY_ID")
    oss_access_key_secret: str = Field(default="", alias="OSS_ACCESS_KEY_SECRET")
    oss_endpoint: str = Field(default="", alias="OSS_ENDPOINT")
    oss_bucket_name: str = Field(default="", alias="OSS_BUCKET_NAME")
    oss_url_expire_seconds: int = Field(default=600, alias="OSS_URL_EXPIRE_SECONDS", gt=0)
    image_generation_model: str = Field(default="gpt-image-2", alias="IMAGE_GENERATION_MODEL")
    account_package_model: str = Field(default="deepseek-v4-flash", alias="ACCOUNT_PACKAGE_MODEL")
    execution_plan_model: str = Field(default="deepseek-v4-flash", alias="EXECUTION_PLAN_MODEL")
    deepseek_topics_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_TOPICS_MODEL")
    deepseek_account_package_model: str = Field(
        default="deepseek-v4-flash",
        alias="DEEPSEEK_ACCOUNT_PACKAGE_MODEL",
    )
    video_generation_base_url: str = Field(default="", alias="VIDEO_GENERATION_BASE_URL")
    ark_api_key: str = Field(default="", alias="ARK_API_KEY")
    video_generation_api_key: str = Field(default="", alias="VIDEO_GENERATION_API_KEY")
    video_generation_model: str = Field(default="seedance-2.0", alias="VIDEO_GENERATION_MODEL")
    video_generation_seedance_2_endpoint: str = Field(
        default="doubao-seedance-2-0-260128",
        alias="VIDEO_GENERATION_SEEDANCE_2_ENDPOINT",
    )
    video_generation_seedance_fast_endpoint: str = Field(
        default="doubao-seedance-2-0-fast-260128",
        alias="VIDEO_GENERATION_SEEDANCE_FAST_ENDPOINT",
    )
    video_generation_enabled_models: str = Field(
        default="seedance-2.0,seedance-2.0-fast",
        alias="VIDEO_GENERATION_ENABLED_MODELS",
    )
    video_generation_timeout_seconds: float = Field(default=300.0, alias="VIDEO_GENERATION_TIMEOUT_SECONDS", gt=0)
    video_parser_api_url: str = Field(default="", alias="VIDEO_PARSER_API_URL")
    video_parser_api_key: str = Field(default="", alias="VIDEO_PARSER_API_KEY")
    asr_api_url: str = Field(default="", alias="ASR_API_URL")
    asr_api_key: str = Field(default="", alias="ASR_API_KEY")
    asr_model_size: str = Field(default="medium", alias="ASR_MODEL_SIZE")
    asr_device: str = Field(default="auto", alias="ASR_DEVICE")
    asr_compute_type: str = Field(default="default", alias="ASR_COMPUTE_TYPE")

    # Digital human services (local)
    cozy_voice_url: str = Field(default="http://127.0.0.1:50000", alias="COZY_VOICE_URL")
    hey_gem_url: str = Field(default="http://127.0.0.1:3000", alias="HEY_GEM_URL")

    # Douyin video parser (local Douyin_TikTok_Download_API)
    douyin_api_url: str = Field(default="http://127.0.0.1:9000", alias="DOUYIN_API_URL")

    model_config = SettingsConfigDict(
        env_file=("../.env.example", "../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    def assert_secure_for_production(self) -> None:
        if not self.is_production:
            return
        if self.auth_secret_key == DEFAULT_DEV_AUTH_SECRET or not self.auth_secret_key.strip():
            raise RuntimeError(
                "AUTH_SECRET_KEY must be set to a strong, non-default value when APP_ENV=production"
            )
        if not self.auth_cookie_secure:
            raise RuntimeError(
                "AUTH_COOKIE_SECURE must be true when APP_ENV=production"
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.assert_secure_for_production()
    return settings
