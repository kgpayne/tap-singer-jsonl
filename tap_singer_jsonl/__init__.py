#!/usr/bin/env python3
import json
import logging
import sys

from singer_sdk._singerlib import Catalog
from smart_open import open

from .utils import get_local_file_paths, parse_args

logger = logging.getLogger(__name__)

files = {
    "local": {
        "folders": [".secrets/test_input/"],
        "paths": ["file://absolute_file/path/stream.jsonl"],
    },
    "s3": {
        "bucket": "my-bucket-name",
        "prefix": "/singer/streams/",
        "paths": ["s3://example_s3_path.jsonl"],
    },
}

REQUIRED_CONFIG_KEYS = []


def extract_schema_messages(file_path):
    schema_messages = []
    for line in open(file_path):
        logger.info(f"Found file {file_path}")
        try:
            line_dict = json.loads(line)
        except json.decoder.JSONDecodeError as exc:
            logger.error("Unable to parse:\n%s", line, exc_info=exc)
            raise

        if line_dict["type"] == "SCHEMA":
            schema_messages.append(line_dict)
    return schema_messages


def load_streams(config):
    """Load schemas from schemas folder"""
    schema_messages = []
    paths = []

    if "local" in config:
        paths.extend(get_local_file_paths(config["local"]))

    for path in paths:
        schema_messages.extend(extract_schema_messages(path))

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
    streams = load_streams(config)
    return Catalog.from_dict(streams)


def sync(config, state, catalog):
    """Sync data from tap source"""
    # Loop over files in config
    if "files" in config:
        for file_path in config["files"]:
            for line in open(file_path):
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
