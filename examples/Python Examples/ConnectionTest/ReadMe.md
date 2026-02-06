# SystemLink Enterprise API Connection Test

This example demonstrates how to test the connection to a SystemLink Enterprise
server by verifying API connectivity and authentication.

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

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Connection refused | Server URL incorrect or server down | Verify the server URL and ensure the server is running |
| 401 Unauthorized | Invalid or expired API key | Generate a new API key |
| SSL Certificate Error | Self-signed certificate | Use `--insecure` flag or configure proper certificates |
