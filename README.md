# `tap-singer-jsonl`

This is a [Singer](https://singer.io) tap that reads raw Singer-formatted messages,
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md), from JSONL files.
The tap expects one Singer message (`SCHEMA`, `RECORD` etc.) per line.
More information about the Singer Spec is available on the Meltano Hub [here](https://hub.meltano.com/singer/spec/).

# Usage

## Installation

```shell
pip install tap-singer-jsonl
```

## Settings

When discovering files (`local` folders or `s3` key prefixes), the tap will only discover files with the extension `.singer.gz`.
This matches the format outputted by [target-singer-jsonl](https://github.com/kgpayne/target-singer-jsonl) and provides interoperability.
File paths passed into `local.paths` and `s3.paths` are not filtered by extension.

Example config:

```python
{
    "source": "local",
    "add_record_metadata": False,
    "local": {
        "folders": [".secrets/test_input/"],
        "recursive": True,
        "paths": ["/absolute_file/path/stream.jsonl", "relative/file/path/stream.singer.gz"],
    },
    # The following would not be used as the `source` flag is configured as `local` above.
    # This approach allows multiple configs to be specified, with just the flag to be overridden
    # in tools like Meltano (rather than the entire config).
    "s3": {
        "bucket": "my-bucket-name",
        "prefix": "/singer/streams/",
        "paths": ["s3://example_s3_path.jsonl"],
    },
}
```

| Setting             | Required | Default | Description                                                                                                                                                                                                 |
| :------------------ | :------: | :-----: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| source              |   True   | `local` | The source configuration to use when reading `.singer.gz` files. Currently `local` and `s3` are supported.                                                                                                  |
| add_record_metadata |  False   | `true`  | Whether to inject `_sdc_*` metadata columns.                                                                                                                                                                |
| local.folders       |  False   |  `[]`   | Array of directory paths to scan for `.singer.gz` files.                                                                                                                                                    |
| local.recursive     |  False   | `false` | Whether to scan directories recursively when discovering `.singer.gz` files.                                                                                                                                |
| local.paths         |  False   |  `[]`   | Array of file paths to singer-formatted files. **Note:** extension is ignored, and compression is inferred automatically by `smart_open`. Both `local.folders` and `local.paths` can be specified together. |
| s3.bucket           |  False   |         | S3 bucket name.                                                                                                                                                                                             |
| s3.prefix           |  False   |         | S3 key prefix. **Note:** key prefixes will be scanned recursively.                                                                                                                                          |
| s3.paths            |  False   |  `[]`   | S3 file paths to singer-formatted files. **Note:** extension is ignored, and compression is inferred automatically by `smart_open`. Both `s3.prefix` and `s3.paths` can be specified together.              |

## Usage

```bash
# pipe tap output to a single file
tap-singer-jsonl --config example_config.json > output/records.jsonl
# pipe tap output to a Singer target
tap-singer-jsonl --config example_config.json | target-csv
```

## Limitations

`tap-singer-jsonl` is in **development** so may not work 100% as expected.
It was also not built using the [Meltano Singer SDK](https://sdk.meltano.com/en/latest/), due to its low-level handling of Singer messages.
This may change in future, however it currently means that advanced features such as `catalog` support and stream-selection are not yet available.

## Testing with [Meltano](https://meltano.com/)

_**Note:** This target will work in any Singer environment and does not require Meltano.
Examples here are for convenience and to streamline end-to-end orchestration scenarios._

Your project comes with a custom `meltano.yml` project file already created.

Next, install Meltano (if you haven't already) and any needed plugins:

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano run job-simple-test
```
