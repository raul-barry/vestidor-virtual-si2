from pydantic import BaseModel, ConfigDict, Field, SecretStr

class PlatformAIConfigUpdate(BaseModel):
    api_key: SecretStr | None = None
    clear_api_key: bool = False
    primary_model: str = Field(min_length=1, max_length=160)
    fast_model: str = Field(min_length=1, max_length=160)
    vision_model: str = Field(min_length=1, max_length=160)
    transcription_model: str = Field(min_length=1, max_length=160)
    capability_models: dict[str, str] | None = None


class PlatformAIModelsRequest(BaseModel):
    api_key: SecretStr | None = None


class PlatformAIConnectionRequest(BaseModel):
    api_key: SecretStr | None = None
    model: str | None = Field(default=None, min_length=1, max_length=160)
    capability: str = "complex_reasoning"


class PlatformAIConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    configured: bool
    masked_api_key: str | None
    primary_model: str
    fast_model: str
    vision_model: str
    transcription_model: str
    capability_models: dict[str, str]
    experimental_models: list[str]
    last_test_status: str | None
    last_test_at: str | None


class PlatformAIModelResponse(BaseModel):
    id: str
    active: bool = True
    experimental: bool = False
    capabilities: list[str] = Field(default_factory=list)
