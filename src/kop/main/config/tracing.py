from pydantic import Field

from kop.main.config.base import BaseConfig


class TracingConfig(BaseConfig):
    header: str = Field(default="X-Trace-Id", min_length=1)
    required: bool = False
