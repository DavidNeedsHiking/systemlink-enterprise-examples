# SystemLink Asset Management API Guide

This guide demonstrates how to interact with the SystemLink Enterprise Asset Management API (`/niapm`) to query, filter, and analyze assets.

## Overview

The Asset Management API allows you to:
- Query and browse assets
- Filter assets by vendor, model, type, calibration status
- Track calibration due dates
- Monitor asset utilization
- Manage asset locations

## Prerequisites

```bash
cd examples/Python\ Examples/ConnectionTest

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Ensure .env is configured
cat .env
# Should contain:
# SYSTEMLINK_API_URL=https://your-api-server.com
# SYSTEMLINK_API_KEY=your-api-key
```

## Using the Query Script

The `query_assets.py` script provides a CLI for exploring assets.

### Basic Commands

```bash
# List assets (default: 20)
python query_assets.py

# Show summary statistics
python query_assets.py --summary

# Limit results
python query_assets.py --take 10

# Show only calibratable assets
python query_assets.py --calibratable

# Get specific asset details
python query_assets.py --asset-id "abc-123-xyz"

# Output raw JSON (for scripting)
python query_assets.py --json-output
```

### Filtering Assets

Use the `--filter` option with SystemLink query syntax. **Note:** Use double quotes for string values.

```bash
# Filter by vendor
python query_assets.py --filter 'vendorName == "National Instruments"'

# Filter by model
python query_assets.py --filter 'modelName == "PXI-4461"'

# Filter by asset type
python query_assets.py --filter 'assetType == "FIXTURE"'

# Combine filters
python query_assets.py --filter 'vendorName == "NI" && assetType == "GENERIC"'
```

### Available Filter Fields

| Field | Description | Example Values |
|-------|-------------|----------------|
| `modelName` | Model name | `"PXI-4461"`, `"MSO4104B"` |
| `modelNumber` | Model number | `0`, `123` |
| `vendorName` | Vendor/manufacturer | `"National Instruments"`, `"Tektronix"` |
| `vendorNumber` | Vendor ID | `0` |
| `serialNumber` | Serial number | `"ABC123"` |
| `assetType` | Asset category | `"DEVICE_UNDER_TEST"`, `"FIXTURE"`, `"GENERIC"`, `"SYSTEM"` |
| `busType` | Connection type | `"TCP_IP"`, `"PXI"`, `"BUILT_IN_SYSTEM"` |
| `workspace` | Workspace ID | `"2b075130-bbd0-40cf-..."` |
| `calibrationStatus` | Calibration state | `"OK"`, `"PAST_RECOMMENDED_DUE_DATE"`, `"APPROACHING_RECOMMENDED_DUE_DATE"` |

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/niapm/v1/assets` | GET | List assets with pagination |
| `/niapm/v1/query-assets` | POST | Query assets with filter expression |
| `/niapm/v1/asset-summary` | GET | Get aggregated statistics |
| `/niapm/v1/assets/{id}` | GET | Get specific asset details |
| `/niapm/v1/assets/{id}/history/calibration` | GET | Get calibration history |

## Examples

### Example 1: Get Server Overview

```bash
python query_assets.py --take 100 --json-output | python3 -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
assets = data.get('assets', [])
total = data.get('totalCount', 0)

vendors = Counter(a.get('vendorName') or 'N/A' for a in assets)
types = Counter(a.get('assetType') or 'N/A' for a in assets)

print(f'Total Assets: {total}')
print('\nAsset Types:')
for t, c in types.most_common(5):
    print(f'  {t}: {c}')
print('\nTop Vendors:')
for v, c in vendors.most_common(5):
    print(f'  {v}: {c}')
"
```

### Example 2: Calibration Due Date Analysis

```bash
python query_assets.py --calibratable --take 500 --json-output | python3 -c "
import sys, json
from datetime import datetime, timedelta
from collections import defaultdict

data = json.load(sys.stdin)
assets = data.get('assets', [])
today = datetime.now()
three_months = today + timedelta(days=90)

by_vendor = defaultdict(lambda: {'overdue': 0, 'due_soon': 0})

for a in assets:
    cal = a.get('externalCalibration', {}) or {}
    next_due_str = cal.get('nextRecommendedDate')
    if not next_due_str:
        continue
    
    try:
        next_due = datetime.fromisoformat(next_due_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        continue
    
    vendor = a.get('vendorName', 'Unknown')
    if next_due < today:
        by_vendor[vendor]['overdue'] += 1
    elif next_due <= three_months:
        by_vendor[vendor]['due_soon'] += 1

print('Calibration Status by Vendor:')
print(f'{\"Vendor\":<30} {\"Overdue\":<10} {\"Due <3mo\":<10}')
print('-' * 50)
for vendor, counts in sorted(by_vendor.items(), key=lambda x: -sum(x[1].values())):
    print(f'{vendor[:28]:<30} {counts[\"overdue\"]:<10} {counts[\"due_soon\"]:<10}')
"
```

### Example 3: Direct API Call with curl

```bash
source .env

# Get asset summary
curl -s -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  "$SYSTEMLINK_API_URL/niapm/v1/asset-summary" | python3 -m json.tool

# Query assets with filter
curl -s -X POST \
  -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  -H "Content-Type: application/json" \
  "$SYSTEMLINK_API_URL/niapm/v1/query-assets" \
  -d '{
    "filter": "vendorName == \"Tektronix\"",
    "skip": 0,
    "take": 10,
    "returnCount": true
  }' | python3 -m json.tool

# Get calibration history for an asset
curl -s -H "X-NI-API-KEY: $SYSTEMLINK_API_KEY" \
  "$SYSTEMLINK_API_URL/niapm/v1/assets/{asset-id}/history/calibration" | python3 -m json.tool
```

## Asset Data Structure

```json
{
  "id": "a0bab249-8d95-44e2-ae21-59b3ea00a067",
  "modelName": "MSO4104B",
  "vendorName": "Tektronix",
  "serialNumber": "C010792",
  "assetType": "GENERIC",
  "busType": "TCP_IP",
  "visaResourceName": "TCPIP0::10.2.135.110::inst0::INSTR",
  "calibrationStatus": "PAST_RECOMMENDED_DUE_DATE",
  "location": {
    "minionId": "NI_PXIe-8880--SN-031062CE",
    "state": {
      "assetPresence": "NOT_PRESENT",
      "systemConnection": "DISCONNECTED"
    }
  },
  "externalCalibration": {
    "date": "2022-12-16T06:00:00.000Z",
    "nextRecommendedDate": "2023-12-16T06:00:00.000Z",
    "recommendedInterval": 12,
    "calibrationType": "EXTERNAL_CALIBRATION"
  },
  "properties": {
    "customField": "customValue"
  },
  "workspace": "e2897cf7-6332-433c-8284-65b7b628f3f6"
}
```

## Calibration Status Values

| Status | Description |
|--------|-------------|
| `OK` | Calibration is current |
| `APPROACHING_RECOMMENDED_DUE_DATE` | Due date is approaching |
| `PAST_RECOMMENDED_DUE_DATE` | Calibration is overdue |

## Related Resources

- [Asset Utilization Example](../../Asset%20Utilization/Utilization%20to%20Tags%20SLE.ipynb)
- [SystemLink API Documentation](https://www.ni.com/docs/en-US/bundle/systemlink-enterprise/)
- [Swagger UI](https://your-api-server.com/niapis/) - Interactive API explorer

---
*Last updated: February 2026*
