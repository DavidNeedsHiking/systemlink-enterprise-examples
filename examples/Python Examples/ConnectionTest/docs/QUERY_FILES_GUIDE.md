# SystemLink File Service Query Tool

A command-line tool to query and manage files in SystemLink Enterprise File Service.

## Features

- 📁 **List files** by workspace or across all workspaces
- 🔍 **Search files** by name (partial match)
- 📊 **View file details** including metadata and custom properties
- 💾 **Download files** directly from the command line
- 📋 **Export to JSON** for integration with other tools
- 🗂️ **List workspaces** with file counts

## Prerequisites

- Python 3.8+
- Virtual environment with dependencies installed

```bash
cd examples/Python\ Examples/ConnectionTest
source .venv/bin/activate
pip install -r ../TestMonitor/requirements.txt
```

## Configuration

The script uses environment variables from `.env`:

```bash
SYSTEMLINK_API_URL=https://your-api-server.com
SYSTEMLINK_API_KEY=your-api-key
```

## Usage Examples

### List All Available Workspaces

```bash
python query_files.py --list-workspaces
```

Output:
```
Available Workspaces
============================================================

Workspace ID                             Files
----------------------------------------------------
ee940aa2-05d3-4585-a822-52f7234a5207        192
e2897cf7-6332-433c-8284-65b7b628f3f6          6
2b075130-bbd0-40cf-b0a8-ecea1c0d5f81          2

Total workspaces: 3
```

### List Files in a Specific Workspace

```bash
python query_files.py --workspace-id ee940aa2-05d3-4585-a822-52f7234a5207
```

### Search Files by Name

```bash
python query_files.py --name "anomaly"
```

Output:
```
SystemLink File Service Query
============================================================
Server: https://test-api.lifecyclesolutions.ni.com
Name filter: anomaly

Found 1 files

Name                                               Created              Size
-------------------------------------------------------------------------------------
anomaly_report.json                                2026-01-22 11:45    20.7 MB

Summary:
  Total files: 1
  Total size: 20.7 MB
```

### Get Detailed File Information

```bash
python query_files.py --file-id 58cdfc9e-522e-4ea2-ade9-bf211c688cc3
```

Output:
```
File Details
----------------------------------------
  Name:           anomaly_report.json
  ID:             58cdfc9e-522e-4ea2-ade9-bf211c688cc3
  Created:        2026-01-22 11:45:40
  Size:           20.7 MB
  Workspace:      ee940aa2-05d3-4585-a822-52f7234a5207
  Service Group:  Default

  Custom Properties:
    guid: xyz77
    success: True

  API Links:
    data: /nifile/v1/service-groups/Default/files/58cdfc9e-.../data
    delete: /nifile/v1/service-groups/Default/files/58cdfc9e-...
    self: /nifile/v1/service-groups/Default/files/58cdfc9e-...
```

### Download a File

```bash
python query_files.py --file-id 58cdfc9e-522e-4ea2-ade9-bf211c688cc3 --download ./anomaly_report.json
```

### Export Results as JSON

```bash
# Export file list to JSON
python query_files.py --workspace-id ee940aa2-... --output json > files.json

# Export workspaces to JSON
python query_files.py --list-workspaces --output json > workspaces.json
```

### Combine Filters

```bash
# Search for files containing "VAL" in a specific workspace
python query_files.py --workspace-id ee940aa2-... --name "VAL" --limit 20
```

## Command Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--server` | | SystemLink API server URL |
| `--api-key` | | SystemLink API key |
| `--workspace-id` | `-wid` | Filter by workspace ID |
| `--name` | `-n` | Filter by file name (partial match) |
| `--file-id` | `-id` | Get details for a specific file |
| `--list-workspaces` | `-lw` | List all workspaces with file counts |
| `--limit` | `-l` | Max files to display (default: 50) |
| `--output` | `-o` | Output format: `table` or `json` |
| `--download` | `-d` | Download file to path (with `--file-id`) |
| `--insecure` | | Skip SSL certificate verification |

## Integration Examples

### Python Script Integration

```python
from query_files import FileServiceClient

# Create client
client = FileServiceClient(
    base_url="https://your-api.com",
    api_key="your-key"
)

# Get files from a workspace
files = client.get_files(
    workspace_id="ee940aa2-05d3-4585-a822-52f7234a5207",
    name_filter="anomaly"
)

for f in files:
    print(f"File: {f['properties']['Name']}")
    print(f"Size: {f['size']} bytes")
```

### Bash Script Integration

```bash
#!/bin/bash

# Export all files as JSON and process with jq
python query_files.py --output json | jq '.[] | {name: .properties.Name, size: .size}'

# Count files by workspace
python query_files.py --list-workspaces --output json | jq 'map(.fileCount) | add'
```

## Known Workspace IDs

For the test environment, here are common workspace IDs:

| Workspace Name | ID |
|---------------|-----|
| Data Science | `ee940aa2-05d3-4585-a822-52f7234a5207` |
| (Other) | `e2897cf7-6332-433c-8284-65b7b628f3f6` |
| (Other) | `2b075130-bbd0-40cf-b0a8-ecea1c0d5f81` |

> **Note:** Workspace names are not directly available from the File API. You may need to check the SystemLink web UI to map IDs to names.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Error: Server URL is required` | Set `SYSTEMLINK_API_URL` in `.env` |
| `Error: API key is required` | Set `SYSTEMLINK_API_KEY` in `.env` |
| `HTTP 401` | API key is invalid or expired |
| `HTTP 403` | Insufficient permissions for this operation |
| `No files found` | Check workspace ID or name filter |

## Related Scripts

- [test_connection.py](test_connection.py) - Quick connection test
- [test_api_functionality.py](test_api_functionality.py) - Full API test suite
