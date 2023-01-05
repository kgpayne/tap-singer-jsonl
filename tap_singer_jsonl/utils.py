import argparse
import fnmatch
import gzip
import io
import json
import logging
import sys
from pathlib import Path

from singer_sdk._singerlib import Catalog
from smart_open import s3

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

logger = logging.getLogger(__name__)


def get_file_lines(source, config):
    if source == "local":
        yield from get_local_file_lines(config)
    elif source == "s3":
        yield from get_s3_file_lines(config)
    else:
        raise Exception(f"Source '{source}' not supported.")


def get_local_file_lines(config):
    paths = get_local_file_paths(config)
    for file_path in paths:
        logger.info(f"Reading file: {file_path}")
        yield from file_path.open("r", encoding="utf-8")


def get_local_file_paths(config):
    paths = config.get("paths", [])
    recursive = config.get("recursive", False)
    if "folders" in config:
        for folder in config["folders"]:
            folder_path = Path(folder)
            if folder_path.is_dir():
                if recursive:
                    files = [
                        str(file) for file in folder_path.rglob("*") if file.is_file()
                    ]
                else:
                    files = [
                        str(file) for file in folder_path.iterdir() if file.is_file()
                    ]
                files = [Path(file) for file in fnmatch.filter(files, "*.singer*")]
                paths.extend(files)
    return list(set(paths))


def get_s3_file_lines(config):
    bucket = config["bucket"]
    prefix = config["prefix"]
    for key, content in s3.iter_bucket(
        bucket, prefix=prefix, accept_key=lambda key: fnmatch.fnmatch(key, "*.singer*")
    ):
        logger.info(f"Reading S3 key: {key}")
        if key.endswith(".gz"):
            content = gzip.decompress(content)
        yield from content.decode("utf-8").splitlines(keepends=True)


def extract_schema_messages(lines):
    schema_messages = []
    for line in lines:
        try:
            line_dict = json.loads(line)
        except json.decoder.JSONDecodeError as exc:
            logger.error("Unable to parse:\n%s", line, exc_info=exc)
            raise

        if line_dict["type"] == "SCHEMA":
            schema_messages.append(line_dict)
    return schema_messages


def get_schema_messages(source, config):
    lines = get_file_lines(source=source, config=config)
    return extract_schema_messages(lines=lines)


def load_json(path):
    with open(path) as fil:
        return json.load(fil)


def check_config(config, required_keys):
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise KeyError(f"Config is missing required keys: {missing_keys}")


def parse_args(required_config_keys):
    """Parse standard command-line args.
    Parses the command-line arguments mentioned in the SPEC and the
    BEST_PRACTICES documents:
    -c,--config     Config file
    -s,--state      State file
    -d,--discover   Run in discover mode
    -p,--properties Properties file: DEPRECATED, please use --catalog instead
    --catalog       Catalog file
    --dev     Runs the tap in dev mode
    Returns the parsed args object from argparse. For each argument that
    point to JSON files (config, state, properties), we will automatically
    load and parse the JSON file.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", help="Config file", required=True)

    parser.add_argument("-s", "--state", help="State file")

    parser.add_argument(
        "-p",
        "--properties",
        help="Property selections: DEPRECATED, Please use --catalog instead",
    )

    parser.add_argument("--catalog", help="Catalog file")

    parser.add_argument(
        "-d", "--discover", action="store_true", help="Do schema discovery"
    )

    parser.add_argument("--dev", action="store_true", help="Runs tap in dev mode")

    args = parser.parse_args()
    if args.config:
        setattr(args, "config_path", args.config)
        args.config = load_json(args.config)
    if args.state:
        setattr(args, "state_path", args.state)
        args.state = load_json(args.state)
    else:
        args.state = {}
    if args.properties:
        setattr(args, "properties_path", args.properties)
        args.properties = load_json(args.properties)
    if args.catalog:
        setattr(args, "catalog_path", args.catalog)
        args.catalog = Catalog.from_dict(load_json(args.catalog))

    check_config(args.config, required_config_keys)

    return args
