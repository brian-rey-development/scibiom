import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, override

from pydantic import SecretStr

from scibiom_api.bootstrap.settings import ApiSettings, Environment
from scibiom_api.main import create_app
from scibiom_infrastructure.database.settings import DatabaseSettings

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

EXPORT_DATABASE_URL = "postgresql+psycopg://export:unused@127.0.0.1:5432/export"


class _ExportSettings(ApiSettings):
    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def _export_settings() -> ApiSettings:
    return _ExportSettings(
        environment=Environment.TEST,
        database=DatabaseSettings(url=SecretStr(EXPORT_DATABASE_URL)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Scibiom API OpenAPI schema to a file.")
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    schema = json.dumps(create_app(_export_settings()).openapi(), indent=2, sort_keys=True)
    arguments.output.write_text(schema + "\n", encoding="utf-8")
