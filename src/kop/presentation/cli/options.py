from pydantic import BaseModel, ConfigDict


class CliOutputOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    quiet: bool = False
    no_color: bool = False
