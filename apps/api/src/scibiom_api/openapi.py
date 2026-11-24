import argparse
import json
from pathlib import Path

from scibiom_api.main import openapi_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Scibiom API OpenAPI schema to a file.")
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    schema = json.dumps(openapi_schema(), indent=2, sort_keys=True)
    arguments.output.write_text(schema + "\n", encoding="utf-8")
