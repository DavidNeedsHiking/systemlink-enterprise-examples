# SystemLink Enterprise API Connection Test

This example demonstrates how to test the connection to a SystemLink Enterprise
server by verifying API connectivity and authentication.

---

## � Folder Structure

```
ConnectionTest/
├── core/           # Reusable libraries
│   ├── systemlink_client.py    # Main API client library
│   └── outlier_detection.py    # Outlier detection module
├── docs/           # API guides and documentation
│   ├── API_WRAPPER_GUIDE.md
│   ├── ASSET_MANAGEMENT_GUIDE.md
│   ├── DATAFRAME_API_GUIDE.md
│   ├── NOTIFICATION_API_GUIDE.md
│   └── QUERY_FILES_GUIDE.md
├── config/         # Project-specific configuration
│   ├── SERVER_INFO.md          # Server details, data sources
│   ├── .env                    # API keys (gitignored)
│   ├── .env.example            # Template
│   └── .gitignore
├── scripts/        # Example scripts and CLI tools
│   ├── query_assets.py
│   ├── query_files.py
│   ├── test_connection.py
│   └── test_api_functionality.py
└── ReadMe.md
```

---

## �📚 Use Cases & Documentation Index

### APIs Explored

| API | Endpoint | Documentation | Use Cases |
|-----|----------|---------------|-----------|
| **Asset Management** | `/niapm` | [ASSET_MANAGEMENT_GUIDE.md](docs/ASSET_MANAGEMENT_GUIDE.md) | Query assets, calibration tracking, vendor analysis |
| **Test Monitor** | `/nitestmonitor` | [API_WRAPPER_GUIDE.md](docs/API_WRAPPER_GUIDE.md) | Query test results, failure analysis, step inspection |
| **Notification** | `/ninotification` | [NOTIFICATION_API_GUIDE.md](docs/NOTIFICATION_API_GUIDE.md) | Send email reports, alerts |
| **DataFrame (Data Tables)** | `/nidataframe` | [DATAFRAME_API_GUIDE.md](docs/DATAFRAME_API_GUIDE.md) | Query tables, read data, statistical analysis |
| **All 30 APIs** | Various | [SystemLink_APIs.md](../../Data/Table/SystemLink_APIs.md) | Complete API reference table |
| **Server Config** | - | [SERVER_INFO.md](config/SERVER_INFO.md) | Server URL, versions, data tables |

### Working Code

| File | Description |
|------|-------------|
| [systemlink_client.py](core/systemlink_client.py) | **Main client library** - Reusable wrappers for Asset, Test Monitor, Notification, DataFrame APIs |
| [outlier_detection.py](core/outlier_detection.py) | **Outlier detection module** - Robust methods for skewed error metrics (log-sigma, MAD, IQR, percentile) |
| [query_assets.py](scripts/query_assets.py) | CLI tool for querying assets with filters |
| [query_files.py](scripts/query_files.py) | CLI tool for querying files |
| [test_connection.py](scripts/test_connection.py) | Connection and authentication test |

### Use Case Examples

| Use Case | API(s) Used | Code Example |
|----------|-------------|--------------|
| **Query all assets** | Asset Mgmt | `AssetClient().get_all()` |
| **Find overdue calibrations** | Asset Mgmt | `AssetClient().get_overdue_calibration()` |
| **Get calibration due in N days** | Asset Mgmt | `AssetClient().get_calibration_due_within(90)` |
| **Aggregate by vendor** | Asset Mgmt | Query + group by `vendorName` |
| **Query test results** | Test Monitor | `TestMonitorClient().query_results(filter=...)` |
| **Analyze failure rates** | Test Monitor | `count_results()` with PASSED/FAILED filters |
| **Get failed test steps** | Test Monitor | `query_steps(result_id=...)` |
| **Send email report** | Notification | `NotificationClient().send_email(to, subject, body)` |
| **Failure alert** | Test Monitor + Notification | Combine failure analysis with email |
| **Query data tables** | DataFrame | `DataFrameClient().query_tables(workspace=...)` |
| **Read table data** | DataFrame | `DataFrameClient().to_dataframe(table_id)` |
| **Analyze table statistics** | DataFrame | `DataFrameClient().summary(table_id)` |
| **Anomaly analysis** | DataFrame + Notification | Read anomaly data, alert on high failure rate |
| **Detect outliers (log-sigma)** | DataFrame + Outlier | `OutlierDetector(df, 'Error_MAE').log_sigma()` |
| **Detect outliers (percentile)** | DataFrame + Outlier | `detector.percentile_upper_only(upper_pct=99)` |
| **Consensus outliers** | Outlier | `detector.consensus(min_methods=3)` |

### Reports & Data

| Report | Location | Description |
|--------|----------|-------------|
| [ESS Failure Analysis](../../Data/ESS_Failure_Analysis_Report.txt) | `Data/` | Analysis of ESS parts failure rates by operator, bay, serial |

### Design Guides

| Guide | Purpose |
|-------|---------|
| [API_WRAPPER_GUIDE.md](docs/API_WRAPPER_GUIDE.md) | How to extend the client library, add new APIs, best practices |
| [NOTIFICATION_API_GUIDE.md](docs/NOTIFICATION_API_GUIDE.md) | Email sending patterns, dynamic strategy format |
| [ASSET_MANAGEMENT_GUIDE.md](docs/ASSET_MANAGEMENT_GUIDE.md) | Asset queries, filter syntax, calibration tracking |
| [DATAFRAME_API_GUIDE.md](docs/DATAFRAME_API_GUIDE.md) | Data Tables queries, filtering, pagination, type conversion |
| [outlier_detection.py](core/outlier_detection.py) | Outlier detection for skewed metrics (log-sigma, MAD, IQR, percentile) |
| [SERVER_INFO.md](config/SERVER_INFO.md) | Server URL, API versions, data tables, known limitations |

---

## Overview

The `test_connection.py` script performs the following checks:

1. **Server Reachability** - Verifies the server URL is accessible
2. **API Authentication** - Validates the API key is valid
3. **Service Status** - Checks the status of core SystemLink services

## Prerequisites

- Python 3.8 or higher
- Required packages (install via `pip install -r ../requirements.txt`)

## Usage

### Option 1: Using Environment Variables (Recommended)

```bash
export SYSTEMLINK_SERVER_URL=https://my-systemlink-server.com
export SYSTEMLINK_API_KEY=my-api-key-here
python test_connection.py
```

### Option 2: Using Command Line Arguments

```bash
python test_connection.py --server <server_url> --api-key <api_key>
```

### Arguments

| Argument | Environment Variable | Description |
|----------|---------------------|-------------|
| `--server` | `SYSTEMLINK_SERVER_URL` | The SystemLink Enterprise server URL |
| `--api-key` | `SYSTEMLINK_API_KEY` | Your SystemLink API key |
| `--insecure` | - | Skip SSL verification (not recommended) |

Command line arguments take precedence over environment variables.

## Expected Output

On successful connection:

```
============================================================
SystemLink Enterprise Connection Test
============================================================

Testing connection to: https://my-systemlink-server.com
------------------------------------------------------------

[✓] Server is reachable
[✓] API authentication successful
[✓] User: john.doe@example.com
[✓] Test Monitor Service: Available

============================================================
Connection test completed successfully!
============================================================
```

On failure, the script will display the specific error encountered.

## How to Generate an API Key

Please refer to the [NI documentation](https://www.ni.com/docs/en-US/bundle/systemlink-enterprise/page/creating-an-api-key.html)
for instructions on generating an API key.

---

## 🔐 Security Considerations for Storing Credentials

### Security Score by Approach

| Approach | Security Score | Best For |
|----------|:-------------:|----------|
| 1. Secrets Manager | ⭐⭐⭐⭐⭐ (5/5) | Production, CI/CD, Teams |
| 2. `.env` file (gitignored) | ⭐⭐⭐ (3/5) | Local development |
| 3. Environment variables (shell) | ⭐⭐ (2/5) | Quick testing |
| 4. Command line arguments | ⭐ (1/5) | One-time use only |

---

### 🥇 Top 3 Recommended Approaches

#### 1. Secrets Manager (Best - Score: 5/5)

Use a dedicated secrets management service for production environments.

**Options:**
- **HashiCorp Vault** - Industry standard, self-hosted or cloud
- **AWS Secrets Manager** - If using AWS infrastructure
- **Azure Key Vault** - If using Azure infrastructure
- **1Password CLI / Bitwarden CLI** - For individual developers

**Example with 1Password CLI:**
```bash
export SYSTEMLINK_API_KEY=$(op read "op://Vault/SystemLink/api-key")
python test_connection.py
```

**Pros:**
- ✅ Encrypted at rest and in transit
- ✅ Access auditing and rotation policies
- ✅ Team-friendly with access controls
- ✅ No secrets in files or history

**Cons:**
- ❌ Requires additional setup/infrastructure
- ❌ May have costs associated

---

#### 2. `.env` File with python-dotenv (Good - Score: 3/5)

Store credentials in a local `.env` file that is **never committed to git**.

**Setup:**

1. Install python-dotenv: `pip install python-dotenv`

2. Create a `.env` file in your project:
```bash
# .env (add to .gitignore!)
SYSTEMLINK_SERVER_URL=https://my-systemlink-server.com
SYSTEMLINK_API_KEY=your-api-key-here
```

3. **Critical:** Add `.env` to your `.gitignore`:
```bash
echo ".env" >> .gitignore
```

4. Load in Python (already supported by click's envvar):
```python
from dotenv import load_dotenv
load_dotenv()  # Add this before running the script
```

**Pros:**
- ✅ Easy to set up
- ✅ Works across terminal sessions
- ✅ Can have different `.env` files per environment

**Cons:**
- ⚠️ Risk of accidental git commit if not careful
- ⚠️ File permissions matter (use `chmod 600 .env`)
- ⚠️ Not suitable for shared/production environments

---

#### 3. Environment Variables in Shell Profile (Okay - Score: 2/5)

Export variables in your shell profile (`.bashrc`, `.zshrc`, etc.).

**Setup:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export SYSTEMLINK_SERVER_URL="https://my-systemlink-server.com"
export SYSTEMLINK_API_KEY="your-api-key-here"
```

Then reload: `source ~/.bashrc`

**Pros:**
- ✅ Simple to set up
- ✅ Available across all terminal sessions
- ✅ No files in project directory

**Cons:**
- ⚠️ Visible in shell history if set interactively
- ⚠️ Visible to all processes running as your user
- ⚠️ Harder to manage multiple environments
- ⚠️ Can leak in error messages or logs

---

### ❌ What NOT to Do

| Practice | Risk Level | Why It's Dangerous |
|----------|:----------:|-------------------|
| Hardcode in source code | 🔴 Critical | Committed to git, visible to everyone |
| Pass on command line | 🟠 High | Visible in `ps`, shell history, logs |
| Store in unencrypted config | 🟠 High | Easily readable by anyone with file access |
| Share via email/Slack | 🟠 High | Persisted in message history |

---

### Quick Security Checklist

- [ ] API key is **not** in any git-tracked file
- [ ] `.env` files are in `.gitignore`
- [ ] API key has **minimum required permissions**
- [ ] API key has an **expiration date** set
- [ ] Using HTTPS (not HTTP) for server URL
- [ ] Regularly rotate API keys

---

## SystemLink Python Client Library

The `systemlink_client.py` module provides a reusable Python wrapper for SystemLink APIs.

### Quick Start

```python
from systemlink_client import get_asset_client, get_testmonitor_client, get_notification_client

# Query assets
with AssetClient() as assets:
    print(assets.summary())
    for asset in assets.iter_all(filter='vendorName == "NI"'):
        print(asset['name'])

# Query test results
with TestMonitorClient() as tm:
    print(tm.summary())
    failed = tm.get_failed_results(limit=10)

# Send email
notif = get_notification_client()
notif.send_email(["user@example.com"], "Subject", "Body")
```

### Available Clients

| Client | API | Key Methods |
|--------|-----|-------------|
| `AssetClient` | `/niapm` | `query()`, `iter_all()`, `count()`, `summary()` |
| `TestMonitorClient` | `/nitestmonitor` | `query_results()`, `iter_results()`, `get_failed_results()` |
| `NotificationClient` | `/ninotification` | `send_email()`, `send_html_email()` |

### Built-in Features

- **Logging**: `import logging; logging.basicConfig(level=logging.INFO)`
- **Context Managers**: `with AssetClient() as c:` for auto session cleanup
- **Retry**: 3 attempts with exponential backoff (requires `pip install tenacity`)
- **Rate Limiting**: 60 calls/min max (requires `pip install ratelimit`)
- **Generators**: `iter_all()` for memory-efficient iteration

See [API_WRAPPER_GUIDE.md](API_WRAPPER_GUIDE.md) for design patterns and extension guide.

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Connection refused | Server URL incorrect or server down | Verify the server URL and ensure the server is running |
| 401 Unauthorized | Invalid or expired API key | Generate a new API key |
| SSL Certificate Error | Self-signed certificate | Use `--insecure` flag or configure proper certificates |
