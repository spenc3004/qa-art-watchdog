# Art QA Watcher

`art-qa-watcher` monitors a folder for incoming art PDF files, looks up contract
metadata in SQL Server, sends the file path and metadata to a QA API, stores the
QA API response in `dbo.art_results`, and then moves the processed PDF into a
`backup/` subfolder.

## What It Does

For each newly created file in the watched directory:

1. Ignores hidden files such as `.DS_Store`.
2. Ignores files that do not match the expected filename pattern.
3. Parses `client_id`, `contract_id`, `order_line`, and `version` from the PDF
   filename.
4. Looks up `no_tagline` and `est_in_home_date` from SQL Server.
5. Calls the QA API with:
   - `pdf_path`
   - `input_date` in `YYYY-MM-DD` format
   - `noTagline`
6. Stores the QA API response JSON in `dbo.art_results.result`.
7. Moves the processed file into `backup/`.

If processing fails for a file, the watcher logs the error and continues
running.

## Expected Filename Format

The watcher only processes PDFs that match these pattern:

```text
<client_id>_<contract_id>_<order_line>_<anything>_unflat<version>.pdf
<client_id>_<contract_id>_<order_line>_<anything>_flat<version>.pdf
```

Example:

```text
123_456789_1_some-mailpiece_unflat2.pdf
123_456789_1_some-mailpiece_flat2.pdf
```

Parsed values:

- `client_id = 123`
- `contract_id = 456789`
- `order_line = 1`
- `version = 2`

Files that do not match this pattern are ignored.

## Requirements

- Python 3.12+
- Access to the target SQL Server database
- Access to the QA API endpoint
- A writable watched directory

Python dependencies:

- `watchdog`
- `mssql-python`
- `python-dotenv`

Install dependencies with:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with:

```dotenv
SQL_SERVER=your-sql-server
SQL_DATABASE=your-database
SQL_USER=your-username
SQL_PASSWORD=your-password
QA_SERVER=http://127.0.0.1:3000
QA_API_KEY=your-api-key
```

### Environment Variables

- `SQL_SERVER`: SQL Server host or host\instance
- `SQL_DATABASE`: Database name
- `SQL_USER`: SQL login username
- `SQL_PASSWORD`: SQL login password
- `QA_SERVER`: QA API endpoint URL
- `QA_API_KEY`: API key sent as `x-api-key`

## Running Locally

Watch the current directory:

```bash
python watcher.py
```

Watch a specific directory:

```bash
python watcher.py /path/to/watched-folder
```

When a matching PDF is dropped into that folder, the watcher will:

- query SQL Server for contract metadata
- send the QA request
- insert the JSON result into SQL Server
- move the PDF into `backup/`

## Example QA Payload

The watcher sends JSON like:

```json
{
  "pdf_path": "/path/to/file.pdf",
  "input_date": "2026-06-03",
  "noTagline": false
}
```

## Deployment Notes

For EC2 + EFS, pass the mounted EFS path as the watcher argument rather than
hardcoding it in code:

```bash
python watcher.py /mnt/efs/art-drop
```

That keeps the deployment-specific watch path outside the application logic and
makes the running target obvious in process config and service definitions.

## Operational Notes

- The watcher uses filesystem creation events from `watchdog`.
- Hidden files are ignored.
- Files inside the `backup/` folder are ignored.
- Non-matching filenames are ignored.
- Per-file errors do not stop the watcher process.

## Troubleshooting

### `Missing required environment variable(s): QA_SERVER, QA_API_KEY`

Add the missing values to `.env` or export them in the shell before starting
the watcher.

### File was ignored

Check:

- the file is a `.pdf`
- the filename matches one of the expected patterns
- the file was created in the watched directory, not already inside `backup/`

### SQL insert succeeds but JSON looks wrong

The watcher stores the QA response using `json.dumps(...)`. Inspect the value in
`dbo.art_results.result` as plain JSON text.

### Watcher keeps running but a file was not processed

Check the console output for:

```text
Failed to process <filename>: <error>
```

The watcher is designed to log the error and continue watching.
