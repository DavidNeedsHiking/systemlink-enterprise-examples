# SystemLink API Wrapper Design Guide

A guide for creating reusable Python wrappers for SystemLink REST APIs.

## Design Pattern

```
┌─────────────────────────────────────────────────────────┐
│                   SystemLinkClient                       │
│  - Authentication (API key)                             │
│  - Base URL management                                  │
│  - HTTP methods: _get(), _post(), _delete()             │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ AssetClient │ │TestMonitor  │ │Notification │
   │             │ │   Client    │ │   Client    │
   └─────────────┘ └─────────────┘ └─────────────┘
```

## Step-by-Step: Adding a New API

### 1. Find the Swagger Specification

```bash
# List available APIs
curl -s "$SYSTEMLINK_API_URL/niapis/swagger-initializer.js" | grep -oP 'url:\s*"\K[^"]+'

# Get specific API spec
curl -s "$SYSTEMLINK_API_URL/{api-name}/swagger/v2/{api-name}-v2.yml"
```

### 2. Create the Client Class

```python
class NewApiClient(SystemLinkClient):
    """Client for {API Name} API (/{endpoint})."""
    
    API_BASE = "/{endpoint}/v1"  # Define base path once
    
    def list_items(self, take: int = 100, filter: Optional[str] = None) -> Dict:
        """List items with optional filtering."""
        params = {"take": take}
        if filter:
            params["filter"] = filter
        return self._get(f"{self.API_BASE}/items", params)
    
    def get_item(self, item_id: str) -> Dict:
        """Get single item by ID."""
        return self._get(f"{self.API_BASE}/items/{item_id}")
    
    def create_item(self, data: Dict) -> Dict:
        """Create a new item."""
        return self._post(f"{self.API_BASE}/items", data)
```

### 3. Add Convenience Methods

```python
    # Pagination helper
    def get_all(self, filter: Optional[str] = None) -> List[Dict]:
        """Get all items (handles pagination)."""
        all_items, skip = [], 0
        while True:
            result = self.list_items(take=1000, skip=skip, filter=filter)
            items = result.get("items", [])
            all_items.extend(items)
            if len(items) < 1000:
                break
            skip += 1000
        return all_items
    
    # Count helper
    def count(self, filter: Optional[str] = None) -> int:
        """Count items matching filter."""
        result = self.list_items(take=1, filter=filter, return_count=True)
        return result.get("totalCount", 0)
    
    # Summary helper
    def summary(self) -> Dict:
        """Get quick statistics."""
        return {
            "total": self.count(),
            "active": self.count(filter="status == 'ACTIVE'"),
        }
```

### 4. Add Factory Function

```python
def get_newapi_client() -> NewApiClient:
    """Get a NewApi client."""
    return NewApiClient()
```

## Best Practices

### Method Naming Convention

| Operation | Method Name Pattern | Example |
|-----------|---------------------|---------|
| List/Query | `list_*`, `query_*` | `list_assets()`, `query_results()` |
| Get single | `get_*`, `get_*_by_id` | `get_asset(id)` |
| Create | `create_*` | `create_result()` |
| Update | `update_*` | `update_asset(id, data)` |
| Delete | `delete_*` | `delete_result(id)` |
| Count | `count_*` | `count_results()` |
| Get all | `get_all_*` | `get_all_assets()` |
| Summary | `summary()` | `summary()` |

### Filter Syntax Reference

```python
# String comparison (note: double quotes inside single quotes)
filter='name == "MyAsset"'
filter='vendorName.Contains("NI")'

# Numeric comparison
filter='calibrationDueDate < "2024-01-01T00:00:00Z"'

# Boolean
filter='isNIAsset == true'

# Combining with AND/OR
filter='vendorName == "NI" && isNIAsset == true'
filter='status == "PASSED" || status == "DONE"'
```

### Error Handling

```python
def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
    """GET with error handling."""
    try:
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.exceptions.HTTPError as e:
        # Log error details for debugging
        print(f"API Error: {e.response.status_code} - {e.response.text[:200]}")
        raise
```

---

## Suggested Improvements

### 1. **Add Retry Logic with Exponential Backoff**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class SystemLinkClient:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
```

### 2. **Add Response Caching**

```python
from functools import lru_cache

class AssetClient(SystemLinkClient):
    @lru_cache(maxsize=100)
    def get_by_id(self, asset_id: str) -> Dict:
        """Cached asset lookup."""
        return self._get(f"/niapm/v1/assets/{asset_id}")
    
    def clear_cache(self):
        """Clear the cache when data changes."""
        self.get_by_id.cache_clear()
```

### 3. **Add Async Support**

```python
import aiohttp
import asyncio

class AsyncSystemLinkClient:
    async def _get(self, endpoint: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}{endpoint}",
                headers={"X-NI-API-KEY": self.api_key}
            ) as resp:
                return await resp.json()

# Usage
async def main():
    client = AsyncAssetClient()
    assets = await client.query()
```

### 4. **Add Logging**

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("systemlink")

class SystemLinkClient:
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        logger.debug(f"GET {endpoint} params={params}")
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        logger.info(f"GET {endpoint} -> {resp.status_code}")
        resp.raise_for_status()
        return resp.json() if resp.text else {}
```

### 5. **Add Type Hints with Dataclasses**

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Asset:
    id: str
    name: str
    model_name: Optional[str] = None
    vendor_name: Optional[str] = None
    serial_number: Optional[str] = None
    is_ni_asset: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Asset":
        return cls(
            id=data["id"],
            name=data["name"],
            model_name=data.get("modelName"),
            vendor_name=data.get("vendorName"),
            serial_number=data.get("serialNumber"),
            is_ni_asset=data.get("isNIAsset", False)
        )

class AssetClient(SystemLinkClient):
    def get_by_id(self, asset_id: str) -> Asset:
        data = self._get(f"/niapm/v1/assets/{asset_id}")
        return Asset.from_dict(data)
```

### 6. **Add Pagination with Generators**

```python
def iter_all(self, filter: Optional[str] = None, batch_size: int = 500):
    """Iterate through all items without loading all into memory."""
    skip = 0
    while True:
        result = self.query(filter=filter, take=batch_size, skip=skip)
        items = result.get("assets", [])
        for item in items:
            yield item
        if len(items) < batch_size:
            break
        skip += batch_size

# Usage - memory efficient for large datasets
for asset in client.iter_all(filter='vendorName == "NI"'):
    process(asset)
```

### 7. **Add Context Manager Support**

```python
class SystemLinkClient:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

# Usage
with AssetClient() as client:
    assets = client.query()
```

### 8. **Add Rate Limiting**

```python
from ratelimit import limits, sleep_and_retry

class SystemLinkClient:
    @sleep_and_retry
    @limits(calls=100, period=60)  # 100 calls per minute
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
```

---

## Quick Reference: Existing Clients

| Client | Import | Key Methods |
|--------|--------|-------------|
| `AssetClient` | `from systemlink_client import get_asset_client` | `query()`, `count()`, `get_overdue_calibration()`, `summary()` |
| `TestMonitorClient` | `from systemlink_client import get_testmonitor_client` | `query_results()`, `query_steps()`, `get_failed_results()`, `summary()` |
| `NotificationClient` | `from systemlink_client import get_notification_client` | `send_email()`, `send_html_email()` |

## Example: Complete Workflow

```python
from systemlink_client import get_asset_client, get_testmonitor_client, get_notification_client

# Get overdue calibrations and recent failures
assets = get_asset_client()
tm = get_testmonitor_client()
notif = get_notification_client()

overdue = assets.get_overdue_calibration()
failures = tm.get_failed_results(limit=10)

# Build and send report
report = f"""
Daily Status Report
===================
Overdue Calibrations: {len(overdue)}
Recent Test Failures: {len(failures)}

Top 5 Overdue Assets:
{chr(10).join(f"- {a['name']}" for a in overdue[:5])}
"""

notif.send_email(
    to=["team@example.com"],
    subject="Daily SystemLink Status",
    body=report
)
```
