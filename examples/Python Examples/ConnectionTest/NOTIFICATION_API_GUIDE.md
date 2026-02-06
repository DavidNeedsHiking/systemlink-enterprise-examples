# SystemLink Notification API Guide

This guide demonstrates how to send emails programmatically using the SystemLink Enterprise Notification API (`/ninotification`).

## Overview

The Notification API allows you to:
- Send emails to specified recipients
- Use pre-defined message templates
- Create reusable address groups
- Integrate notifications into automated workflows

## Prerequisites

```bash
cd examples/Python\ Examples/ConnectionTest

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Ensure .env is configured with valid credentials
source .env
echo $SYSTEMLINK_API_URL
echo $SYSTEMLINK_API_KEY
```

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ninotification/v1/apply-dynamic-strategy` | POST | Send notification with inline config |
| `/ninotification/v1/notification-strategies` | GET/POST | Manage saved strategies |
| `/ninotification/v1/notification-strategies/{id}/apply` | POST | Apply a saved strategy |
| `/ninotification/v1/address-groups` | GET/POST | Manage recipient groups |
| `/ninotification/v1/message-templates` | GET/POST | Manage message templates |

## Sending Emails

### Method 1: Dynamic Strategy (Inline Configuration)

This method sends an email with all configuration inline - no pre-saved templates required.

```bash
source .env && curl -s -w "\nHTTP Status: %{http_code}\n" -X POST \
  -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  -H "Content-Type: application/json" \
  "$SYSTEMLINK_API_URL/ninotification/v1/apply-dynamic-strategy" \
  -d '{
    "notificationStrategy": {
      "notificationConfigurations": [
        {
          "addressGroup": {
            "interpretingServiceName": "smtp",
            "displayName": "Report Recipients",
            "fields": {
              "toAddresses": ["recipient@example.com"],
              "ccAddresses": ["cc-recipient@example.com"]
            }
          },
          "messageTemplate": {
            "interpretingServiceName": "smtp",
            "displayName": "Report Email",
            "fields": {
              "subjectTemplate": "Your Report Subject",
              "bodyTemplate": "Email body content here.\n\nSupports multiple lines."
            }
          }
        }
      ]
    }
  }'
```

**Success Response:** HTTP 204 (No Content) - Email queued for delivery

### Method 2: Python Script

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_email(to_addresses: list, subject: str, body: str, cc_addresses: list = None):
    """Send an email via SystemLink Notification API."""
    
    url = f"{os.getenv('SYSTEMLINK_API_URL')}/ninotification/v1/apply-dynamic-strategy"
    headers = {
        "X-NI-API-KEY": os.getenv("SYSTEMLINK_API_KEY"),
        "Content-Type": "application/json"
    }
    
    address_fields = {"toAddresses": to_addresses}
    if cc_addresses:
        address_fields["ccAddresses"] = cc_addresses
    
    payload = {
        "notificationStrategy": {
            "notificationConfigurations": [
                {
                    "addressGroup": {
                        "interpretingServiceName": "smtp",
                        "displayName": "Dynamic Recipients",
                        "fields": address_fields
                    },
                    "messageTemplate": {
                        "interpretingServiceName": "smtp",
                        "displayName": "Dynamic Message",
                        "fields": {
                            "subjectTemplate": subject,
                            "bodyTemplate": body
                        }
                    }
                }
            ]
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 204:
        print(f"✓ Email sent successfully to {', '.join(to_addresses)}")
        return True
    else:
        print(f"✗ Failed to send email: {response.status_code}")
        print(response.text)
        return False


# Example usage
if __name__ == "__main__":
    send_email(
        to_addresses=["recipient@example.com"],
        subject="Test Email from SystemLink",
        body="This is a test email.\n\nSent via the Notification API."
    )
```

## Request Schema

### Address Group

```json
{
  "interpretingServiceName": "smtp",
  "displayName": "My Recipients",
  "fields": {
    "toAddresses": ["user1@example.com", "user2@example.com"],
    "ccAddresses": ["cc@example.com"],
    "bccAddresses": ["bcc@example.com"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `interpretingServiceName` | string | Must be `"smtp"` for email |
| `displayName` | string | Friendly name for the group |
| `fields.toAddresses` | array | Primary recipients |
| `fields.ccAddresses` | array | CC recipients (optional) |
| `fields.bccAddresses` | array | BCC recipients (optional) |

### Message Template

```json
{
  "interpretingServiceName": "smtp",
  "displayName": "My Template",
  "fields": {
    "subjectTemplate": "Email Subject",
    "bodyTemplate": "Email body content"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `interpretingServiceName` | string | Must be `"smtp"` for email |
| `displayName` | string | Friendly name for the template |
| `fields.subjectTemplate` | string | Email subject line |
| `fields.bodyTemplate` | string | Email body (plain text, supports `\n` for newlines) |

## Example: Calibration Report Email

```bash
source .env && curl -s -w "\nHTTP Status: %{http_code}\n" -X POST \
  -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  -H "Content-Type: application/json" \
  "$SYSTEMLINK_API_URL/ninotification/v1/apply-dynamic-strategy" \
  -d '{
    "notificationStrategy": {
      "notificationConfigurations": [
        {
          "addressGroup": {
            "interpretingServiceName": "smtp",
            "displayName": "Calibration Team",
            "fields": {
              "toAddresses": ["calibration-team@example.com"]
            }
          },
          "messageTemplate": {
            "interpretingServiceName": "smtp",
            "displayName": "Calibration Report",
            "fields": {
              "subjectTemplate": "Weekly Calibration Status Report",
              "bodyTemplate": "CALIBRATION STATUS REPORT\n\n=== SUMMARY ===\nTotal Calibratable Assets: 263\nOverdue: 141\nDue within 3 months: 3\n\n=== ACTION REQUIRED ===\n1. NI PXIe-4081 (021E4C3B) - Due: 2026-02-12\n2. NI PXI-4110 (01D2406C) - Due: 2026-04-18\n\n---\nGenerated by SystemLink Enterprise"
            }
          }
        }
      ]
    }
  }'
```

## Template Substitution

You can use placeholders in templates that get replaced at send time:

```bash
curl -X POST ... -d '{
    "messageTemplateSubstitutionFields": {
        "assetCount": "263",
        "overdueCount": "141",
        "reportDate": "2026-02-06"
    },
    "notificationStrategy": {
      "notificationConfigurations": [
        {
          "messageTemplate": {
            "fields": {
              "subjectTemplate": "Calibration Report - {{reportDate}}",
              "bodyTemplate": "Total Assets: {{assetCount}}\nOverdue: {{overdueCount}}"
            }
          }
        }
      ]
    }
  }'
```

## Response Codes

| Code | Meaning |
|------|---------|
| 204 | Success - notification queued for delivery |
| 400 | Bad request - check payload format |
| 401 | Unauthorized - check API key |
| 403 | Forbidden - insufficient permissions |
| 500 | Server error - SMTP configuration issue |

## Troubleshooting

### Email not received
1. Check spam/junk folder
2. Verify SMTP is configured on the SystemLink server
3. Check API response code is 204
4. Verify recipient email address is correct

### Authentication errors
```bash
# Test API key validity
curl -s -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  "$SYSTEMLINK_API_URL/ninotification/v1" | python3 -m json.tool
```

### Check available endpoints
```bash
curl -s "$SYSTEMLINK_API_URL/ninotification/swagger/v1/ninotification.json" | \
  python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['paths'].keys()))"
```

## Related Resources

- [Notification API Swagger](https://your-api-server.com/niapis/) - Select "Notification" from dropdown
- [Asset Management Guide](ASSET_MANAGEMENT_GUIDE.md) - Query assets for reports
- [SystemLink Documentation](https://www.ni.com/docs/en-US/bundle/systemlink-enterprise/)

---
*Last updated: February 2026*
