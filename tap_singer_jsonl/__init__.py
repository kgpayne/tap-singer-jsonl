#!/usr/bin/env python3
import json
import logging
import sys
from pathlib import Path

from singer_sdk._singerlib import Catalog
from smart_open.smart_open_lib import patch_pathlib

from .utils import get_file_lines, get_schema_messages, parse_args

_ = patch_pathlib()  # replace `Path.open` with `smart_open.open`

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger(__name__)

example_config = {
    "source": "local",
    "local": {
        "folders": [".secrets/test_input/"],
        "recursive": True,
        "paths": ["file://absolute_file/path/stream.jsonl"],
    },
    "s3": {
        "bucket": "my-bucket-name",
        "prefix": "/singer/streams/",
        "paths": ["s3://example_s3_path.jsonl"],
    },
    "add_record_metadata": False,
}

REQUIRED_CONFIG_KEYS = []


def load_streams(source, config):
    """Load streams from read files."""

    schema_messages = get_schema_messages(source=source, config=config)

    # load via a dictionary to dedupe streams when multiple schema messages are read
    schema = {
        schema_message["stream"]: {
            "tap_stream_id": schema_message["stream"],
            "schema": schema_message["schema"],
            "key_properties": schema_message["key_properties"],
            "metadata": [],
        }
        for schema_message in schema_messages
    }
    return {"streams": list(schema.values())}


def discover(config):
    source = config.get("source", "local")
    streams = load_streams(source, config[source])
    return Catalog.from_dict(streams)


def sync(config, state, catalog):
    """Sync data from tap source"""
    source = config.get("source", "local")
    add_record_metadata = config.get("add_record_metadata", True)
    # Loop over discovered files
    for file_name, row_number, line in get_file_lines(
        source=source, config=config[source]
    ):
        try:
            message = json.loads(line)
        except json.decoder.JSONDecodeError:
            logger.error(f"Unable to parse:\n{line}")
            raise

        if "type" not in message:
            raise Exception(f"Line is missing required key 'type': {line}")
        t = message["type"]

        if t != "STATE" and "stream" not in message:
            raise Exception(f"Line is missing required key 'stream': {line}")

        if t == "RECORD":
            if add_record_metadata:
                record = message["record"]
                record.update(
                    {"_sdc_source_file": file_name, "_sdc_source_lineno": row_number}
                )
            sys.stdout.write(json.dumps(message) + "\n")

        elif t == "SCHEMA":
            if add_record_metadata:
                schema = message["schema"]
                properties_dict = schema["properties"]
                properties_dict["_sdc_source_file"] = {
                    "type": ["string"],
                }
                properties_dict["_sdc_source_lineno"] = {
                    "type": ["integer"],
                }
            sys.stdout.write(json.dumps(message) + "\n")

        else:
            sys.stdout.write(line)

        sys.stdout.flush()


def main():
    # Parse command line arguments
    args = parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover(args.config)
        print(json.dumps(catalog.to_dict(), indent=2))

    # Otherwise run in sync mode
    else:
        if args.catalog:
            catalog = args.catalog
        else:
            catalog = discover(args.config)
        sync(args.config, args.state, catalog)


if __name__ == "__main__":
    main()
