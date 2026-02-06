# SystemLink Enterprise Connection Test Scripts

This guide explains how to use the Python connection test scripts to verify connectivity to your SystemLink Enterprise server.

> **See also:** [Available APIs Overview](../Data/Table/SystemLink_APIs.md) - Complete list of all 30 SystemLink APIs with links to examples *(static, may be outdated)*

## Overview

The `ConnectionTest` folder contains scripts to test API connectivity and verify your configuration before running other examples in this repository.

| Script | Purpose |
|--------|---------|
| `test_connection.py` | Quick connection and authentication check |
| `test_api_functionality.py` | Comprehensive API functionality test across multiple services |

## Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

## Quick Start

### 1. Set Up the Environment

```bash
cd examples/Python\ Examples/ConnectionTest

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r ../TestMonitor/requirements.txt
```

### 2. Configure Credentials

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

#### Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `SYSTEMLINK_API_URL` | ✓ | The SystemLink API endpoint URL |
| `SYSTEMLINK_API_KEY` | ✓ | Your SystemLink API key |
| `SYSTEMLINK_SERVER_URL` | | Main server URL (fallback for API URL) |
| `SYSTEMLINK_SWAGGER_URL` | | Swagger/OpenAPI documentation URL |

#### Example `.env` Configuration

```bash
# API endpoint for making requests
SYSTEMLINK_API_URL=https://your-instance-api.example.com

# Your API key (generate from SystemLink UI)
SYSTEMLINK_API_KEY=your-api-key-here

# Optional: Main server URL
SYSTEMLINK_SERVER_URL=https://your-instance.example.com

# Optional: Swagger documentation URL
SYSTEMLINK_SWAGGER_URL=https://your-instance-api.example.com/niapis/
```

### 3. Run the Tests

```bash
# Activate virtual environment if not already active
source .venv/bin/activate

# Quick connection check
python test_connection.py

# Full API functionality test
python test_api_functionality.py
```

## Command Line Options

Both scripts support command line options that override environment variables:

```bash
# Specify server and API key directly
python test_connection.py --server https://api.example.com --api-key YOUR_KEY

# Skip SSL verification (for self-signed certificates)
python test_connection.py --insecure

# Show help
python test_connection.py --help
```

## Understanding the Output

### Successful Connection

```
============================================================
SystemLink Enterprise Connection Test
============================================================

Testing connection to: https://your-api-server.com
------------------------------------------------------------

[✓] Server is reachable
[✓] API authentication successful
[✓] User: user@example.com
[✓] Test Monitor Service: Available
[✓] File Service: Available
[✓] Tag Service: Available

============================================================
Connection test completed successfully!
============================================================
```

### Failed Connection

```
[✗] Authentication failed: Invalid or expired API key
```

## Services Tested

The `test_api_functionality.py` script tests these SystemLink services:

| Service | Endpoint | Description |
|---------|----------|-------------|
| Authentication | `/niauth/v1/auth` | Validates API key |
| Tag Service | `/nitag/v2/tags` | Tag management |
| Test Monitor | `/nitestmonitor/v2/results` | Test results and steps |
| File Service | `/nifile/v1/service-groups/Default/files` | File storage |
| Alarm Service | `/nialarm/v1/query-instances` | Alarm management |
| Systems Management | `/nisysmgmt/v1/query-systems` | System registration |

## Finding Your API URLs

### Server URL vs API URL

Some SystemLink Enterprise deployments use separate URLs:

- **Server URL**: The main web interface (e.g., `https://systemlink.example.com`)
- **API URL**: The API endpoint (e.g., `https://systemlink-api.example.com`)

### Swagger Documentation

To find available API endpoints and test them interactively:

1. Set the `SYSTEMLINK_SWAGGER_URL` in your `.env` file
2. Open the URL in your browser
3. Use "Authorize" button with your API key to test endpoints

Common Swagger URL patterns:
- `https://your-api-server.com/niapis/`
- `https://your-api-server.com/swagger/`

## Generating an API Key

1. Log in to your SystemLink Enterprise web interface
2. Navigate to **Security** → **API Keys**
3. Click **Create API Key**
4. Set appropriate permissions and expiration
5. Copy the key (it's only shown once!)

For detailed instructions, see the [NI documentation](https://www.ni.com/docs/en-US/bundle/systemlink-enterprise/page/creating-an-api-key.html).

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| `Connection refused` | Wrong URL or server down | Verify the API URL is correct |
| `401 Unauthorized` | Invalid/expired API key | Generate a new API key |
| `SSL Certificate Error` | Self-signed certificate | Use `--insecure` flag |
| `Connection Timeout` | Network/firewall issue | Check network connectivity |

## Security Best Practices

⚠️ **Never commit your `.env` file to version control!**

The `.gitignore` file is configured to exclude:
- `.env`
- `.env.local`
- `.env.*.local`

See the [ReadMe.md](../../examples/Python%20Examples/ConnectionTest/ReadMe.md) in the ConnectionTest folder for detailed security recommendations.

## Related Examples

After verifying connectivity, explore other examples:

- [TestMonitor Examples](../../examples/Python%20Examples/TestMonitor/) - Create and manage test results
- [Script Analysis Examples](../../examples/Script%20Analysis%20Examples/) - Analyze test data
- [Simple ETL Example](../../examples/Simple%20ETL%20Example/) - Data extraction and loading
