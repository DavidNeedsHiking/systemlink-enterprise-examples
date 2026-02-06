"""
SystemLink Enterprise API Client

A reusable Python wrapper for SystemLink REST APIs.
Supports: Asset Management, Test Monitor, Notification, and generic API calls.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Iterator
from dotenv import load_dotenv

# Configure module logger
logger = logging.getLogger("systemlink")
logger.addHandler(logging.NullHandler())  # No output unless user configures logging

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise

# Optional: retry with exponential backoff
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logger.debug("tenacity not installed - retry disabled")

# Optional: rate limiting
try:
    from ratelimit import limits, sleep_and_retry
    RATELIMIT_AVAILABLE = True
except ImportError:
    RATELIMIT_AVAILABLE = False
    logger.debug("ratelimit not installed - rate limiting disabled")


# Retry configuration: 3 attempts with exponential backoff (1s, 2s, 4s)
def _create_retry_decorator():
    """Create retry decorator if tenacity is available."""
    if TENACITY_AVAILABLE:
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((requests.exceptions.ConnectionError,
                                           requests.exceptions.Timeout)),
            before_sleep=lambda retry_state: logger.warning(
                f"Retry {retry_state.attempt_number}/3 after error: {retry_state.outcome.exception()}"
            )
        )
    return lambda func: func  # No-op decorator


# Rate limit configuration: 60 calls per minute (1 per second average)
class _RateLimiter:
    """Simple rate limiter using ratelimit library if available."""
    _limiter = None
    
    @classmethod
    def wait(cls):
        """Wait if rate limit reached. No-op if ratelimit not installed."""
        if cls._limiter is None and RATELIMIT_AVAILABLE:
            @sleep_and_retry
            @limits(calls=60, period=60)
            def _limited():
                pass
            cls._limiter = _limited
        if cls._limiter:
            cls._limiter()


_retry_decorator = _create_retry_decorator()

# Determine .env file location (check config/ folder first, then current directory)
def _find_env_file():
    """Find .env file in config/ folder or current directory."""
    import pathlib
    # Check relative to this module (core/../config/.env)
    module_dir = pathlib.Path(__file__).parent
    config_env = module_dir.parent / "config" / ".env"
    if config_env.exists():
        return str(config_env)
    # Check current working directory
    cwd_env = pathlib.Path.cwd() / ".env"
    if cwd_env.exists():
        return str(cwd_env)
    # Check config/ relative to cwd
    cwd_config_env = pathlib.Path.cwd() / "config" / ".env"
    if cwd_config_env.exists():
        return str(cwd_config_env)
    return None  # Let load_dotenv use its default behavior


class SystemLinkClient:
    """Base client for SystemLink Enterprise APIs."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        env_file = _find_env_file()
        load_dotenv(env_file)
        self.base_url = (base_url or os.getenv("SYSTEMLINK_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("SYSTEMLINK_API_KEY", "")
        
        if not self.base_url or not self.api_key:
            raise ValueError("SYSTEMLINK_API_URL and SYSTEMLINK_API_KEY required")
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-NI-API-KEY": self.api_key,
            "Content-Type": "application/json"
        })
        logger.debug(f"Initialized client for {self.base_url}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.debug("Session closed")

    def _make_request_impl(self, method: str, endpoint: str, 
                           params: Optional[Dict] = None, data: Optional[Dict] = None) -> requests.Response:
        """Internal method to make HTTP request."""
        url = f"{self.base_url}{endpoint}"
        
        if method == "GET":
            resp = self.session.get(url, params=params)
        elif method == "POST":
            resp = self.session.post(url, json=data)
        elif method == "DELETE":
            resp = self.session.delete(url)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return resp

    def _make_request(self, method: str, endpoint: str,
                      params: Optional[Dict] = None, data: Optional[Dict] = None) -> requests.Response:
        """HTTP request with retry and rate limiting."""
        # Apply rate limiting (waits if limit reached)
        _RateLimiter.wait()
        
        if TENACITY_AVAILABLE:
            # Apply retry for connection errors and timeouts
            @_retry_decorator
            def _with_retry():
                return self._make_request_impl(method, endpoint, params, data)
            return _with_retry()
        return self._make_request_impl(method, endpoint, params, data)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET request to API endpoint."""
        logger.debug(f"GET {endpoint} params={params}")
        resp = self._make_request("GET", endpoint, params=params)
        logger.info(f"GET {endpoint} -> {resp.status_code}")
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """POST request to API endpoint."""
        logger.debug(f"POST {endpoint}")
        resp = self._make_request("POST", endpoint, data=data)
        logger.info(f"POST {endpoint} -> {resp.status_code}")
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def _delete(self, endpoint: str) -> bool:
        """DELETE request to API endpoint."""
        logger.debug(f"DELETE {endpoint}")
        resp = self._make_request("DELETE", endpoint)
        logger.info(f"DELETE {endpoint} -> {resp.status_code}")
        resp.raise_for_status()
        return resp.status_code in (200, 204)


class AssetClient(SystemLinkClient):
    """Client for Asset Management API (/niapm)."""

    def query(self, filter: Optional[str] = None, take: int = 100, 
              skip: int = 0, return_count: bool = False) -> Dict:
        """Query assets with optional filter."""
        params = {"take": take, "skip": skip}
        if filter:
            params["filter"] = filter
        if return_count:
            params["returnCount"] = "true"
        return self._get("/niapm/v1/assets", params)

    def get_all(self, filter: Optional[str] = None, batch_size: int = 1000) -> List[Dict]:
        """Get all assets matching filter (handles pagination)."""
        return list(self.iter_all(filter=filter, batch_size=batch_size))

    def iter_all(self, filter: Optional[str] = None, batch_size: int = 1000) -> Iterator[Dict]:
        """Iterate through all assets matching filter (memory-efficient)."""
        skip = 0
        while True:
            result = self.query(filter=filter, take=batch_size, skip=skip)
            assets = result.get("assets", [])
            logger.debug(f"iter_all: fetched {len(assets)} assets at skip={skip}")
            for asset in assets:
                yield asset
            if len(assets) < batch_size:
                break
            skip += batch_size

    def get_by_id(self, asset_id: str) -> Dict:
        """Get single asset by ID."""
        return self._get(f"/niapm/v1/assets/{asset_id}")

    def count(self, filter: Optional[str] = None) -> int:
        """Count assets matching filter."""
        result = self.query(filter=filter, take=1, return_count=True)
        return result.get("totalCount", 0)

    def get_calibratable(self) -> List[Dict]:
        """Get all calibratable assets."""
        return self.get_all(filter="isNIAsset == true")

    def get_overdue_calibration(self) -> List[Dict]:
        """Get assets with overdue calibration."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.get_all(filter=f'isNIAsset == true && calibrationDueDate < "{now}"')

    def get_calibration_due_within(self, days: int) -> List[Dict]:
        """Get assets due for calibration within N days."""
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.get_all(
            filter=f'isNIAsset == true && calibrationDueDate >= "{now_str}" && calibrationDueDate <= "{future}"'
        )

    def summary(self) -> Dict:
        """Get summary statistics of assets."""
        total = self.count()
        calibratable = self.count(filter="isNIAsset == true")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        overdue = self.count(filter=f'isNIAsset == true && calibrationDueDate < "{now}"')
        return {
            "total": total,
            "calibratable": calibratable,
            "overdue_calibration": overdue
        }


class TestMonitorClient(SystemLinkClient):
    """Client for Test Monitor API (/nitestmonitor)."""

    def query_results(self, filter: Optional[str] = None, take: int = 100,
                      return_count: bool = False) -> Dict:
        """Query test results."""
        body = {"take": take}
        if filter:
            body["filter"] = filter
        if return_count:
            body["returnCount"] = True
        return self._post("/nitestmonitor/v2/query-results", body)

    def get_all_results(self, filter: Optional[str] = None, batch_size: int = 500, 
                        max_results: int = 10000) -> List[Dict]:
        """Get test results matching filter (up to max_results)."""
        return list(self.iter_results(filter=filter, max_results=max_results))

    def iter_results(self, filter: Optional[str] = None, batch_size: int = 500,
                     max_results: int = 10000) -> Iterator[Dict]:
        """Iterate through test results matching filter (memory-efficient)."""
        result = self.query_results(filter=filter, take=min(batch_size, max_results))
        results = result.get("results", [])
        logger.debug(f"iter_results: fetched {len(results)} results")
        for r in results:
            yield r

    def count_results(self, filter: Optional[str] = None) -> int:
        """Count test results matching filter."""
        result = self.query_results(filter=filter, take=1, return_count=True)
        return result.get("totalCount", 0)

    def query_steps(self, result_id: Optional[str] = None, filter: Optional[str] = None,
                    take: int = 100, skip: int = 0) -> Dict:
        """Query test steps."""
        body = {"take": take, "skip": skip}
        if result_id:
            body["filter"] = f'resultId == "{result_id}"'
        elif filter:
            body["filter"] = filter
        return self._post("/nitestmonitor/v2/query-steps", body)

    def query_products(self, filter: Optional[str] = None, take: int = 100) -> Dict:
        """Query products."""
        body = {"take": take}
        if filter:
            body["filter"] = filter
        return self._post("/nitestmonitor/v2/query-products", body)

    def get_failed_results(self, limit: int = 100) -> List[Dict]:
        """Get recent failed test results."""
        result = self.query_results(
            filter='status.statusType == "FAILED"',
            take=limit
        )
        return result.get("results", [])

    def summary(self, sample_size: int = 500) -> Dict:
        """Get summary statistics of test results."""
        total = self.count_results()
        sample = self.query_results(take=sample_size)
        
        status_counts = {}
        programs = {}
        operators = {}
        
        for r in sample.get("results", []):
            status = r.get("status", {}).get("statusType", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            prog = r.get("programName", "Unknown")
            programs[prog] = programs.get(prog, 0) + 1
            
            op = r.get("operator", "Unknown")
            operators[op] = operators.get(op, 0) + 1
        
        return {
            "total_results": total,
            "sample_size": sample_size,
            "status_distribution": dict(sorted(status_counts.items(), key=lambda x: -x[1])),
            "top_programs": dict(sorted(programs.items(), key=lambda x: -x[1])[:5]),
            "top_operators": dict(sorted(operators.items(), key=lambda x: -x[1])[:5])
        }


class NotificationClient(SystemLinkClient):
    """Client for Notification API (/ninotification)."""

    def send_email(self, to: List[str], subject: str, body: str,
                   cc: Optional[List[str]] = None) -> bool:
        """Send an email notification."""
        address_fields = {"toAddresses": to}
        if cc:
            address_fields["ccAddresses"] = cc
        
        data = {
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
        
        resp = self.session.post(
            f"{self.base_url}/ninotification/v1/apply-dynamic-strategy",
            json=data
        )
        return resp.status_code == 204

    def send_html_email(self, to: List[str], subject: str, html_body: str) -> bool:
        """Send an HTML email."""
        return self.send_email(to, subject, html_body)


class DataFrameClient(SystemLinkClient):
    """Client for DataFrame API (/nidataframe).
    
    Reads and writes data tables (DataFrames) in SystemLink.
    Handles type conversion for numpy/pandas types.
    """

    def query_tables(self, filter: Optional[str] = None, take: int = 100,
                     workspace: Optional[str] = None) -> Dict:
        """Query available data tables."""
        body = {"take": take}
        if filter:
            body["filter"] = filter
        if workspace:
            body["filter"] = f'workspace == "{workspace}"' + (f" && {filter}" if filter else "")
        return self._post("/nidataframe/v1/query-tables", body)

    def get_table(self, table_id: str) -> Dict:
        """Get table metadata by ID."""
        return self._get(f"/nidataframe/v1/tables/{table_id}")

    def query_data(self, table_id: str, take: int = 1000,
                   filters: Optional[List[Dict]] = None,
                   order_by: Optional[List[Dict]] = None,
                   continuation_token: Optional[str] = None) -> Dict:
        """Query table data with pagination.
        
        Args:
            table_id: The table ID
            take: Number of rows to fetch (max ~2000)
            filters: List of filter dicts like {"column": "name", "operation": "EQUALS", "value": "x"}
            order_by: List of order dicts like {"column": "col", "descending": True}
            continuation_token: Token for pagination
            
        Returns:
            Dict with 'frame' (columns, data), 'totalRowCount', 'continuationToken'
        """
        body = {"take": take}
        if filters:
            body["filters"] = filters
        if order_by:
            body["orderBy"] = order_by
        if continuation_token:
            body["continuationToken"] = continuation_token
        return self._post(f"/nidataframe/v1/tables/{table_id}/query-data", body)

    def iter_table_data(self, table_id: str, batch_size: int = 2000,
                        filters: Optional[List[Dict]] = None,
                        order_by: Optional[List[Dict]] = None) -> Iterator[List]:
        """Iterate through all table rows (memory-efficient).
        
        Yields rows as lists. Use get_table() to get column names.
        """
        continuation_token = None
        while True:
            result = self.query_data(
                table_id, take=batch_size, filters=filters,
                order_by=order_by, continuation_token=continuation_token
            )
            rows = result.get("frame", {}).get("data", [])
            logger.debug(f"iter_table_data: fetched {len(rows)} rows")
            for row in rows:
                yield row
            continuation_token = result.get("continuationToken")
            if not continuation_token:
                break

    def get_all_data(self, table_id: str, batch_size: int = 2000,
                     filters: Optional[List[Dict]] = None) -> Dict:
        """Get all table data as a dict with columns and data.
        
        Returns:
            Dict with 'columns' (list of names) and 'data' (list of row lists)
        """
        # Get column names first
        meta = self.get_table(table_id)
        columns = [c["name"] for c in meta.get("columns", [])]
        
        # Collect all rows
        all_rows = list(self.iter_table_data(table_id, batch_size, filters))
        
        return {"columns": columns, "data": all_rows, "metadata": meta}

    def to_dataframe(self, table_id: str, batch_size: int = 2000,
                     filters: Optional[List[Dict]] = None):
        """Load table data as a pandas DataFrame.
        
        Requires pandas to be installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for to_dataframe(). Install with: pip install pandas")
        
        data = self.get_all_data(table_id, batch_size, filters)
        return pd.DataFrame(data["data"], columns=data["columns"])

    def get_table_by_name(self, name: str, workspace: Optional[str] = None) -> Optional[Dict]:
        """Find a table by name (returns first match)."""
        filter_str = f'name == "{name}"'
        if workspace:
            filter_str = f'workspace == "{workspace}" && {filter_str}'
        result = self.query_tables(filter=filter_str, take=1)
        tables = result.get("tables", [])
        return tables[0] if tables else None

    def summary(self, table_id: str, sample_size: int = 500) -> Dict:
        """Get summary statistics for a table."""
        meta = self.get_table(table_id)
        columns = meta.get("columns", [])
        row_count = meta.get("rowCount", 0)
        
        # Sample data for statistics
        result = self.query_data(table_id, take=sample_size)
        rows = result.get("frame", {}).get("data", [])
        col_names = result.get("frame", {}).get("columns", [])
        
        # Find numeric columns for stats
        numeric_cols = [c for c in columns if c.get("dataType") in 
                       ("INT32", "INT64", "FLOAT32", "FLOAT64")]
        
        numeric_stats = {}
        for col in numeric_cols:
            col_idx = col_names.index(col["name"]) if col["name"] in col_names else -1
            if col_idx >= 0:
                values = []
                for row in rows:
                    try:
                        val = float(row[col_idx])
                        values.append(val)
                    except (ValueError, TypeError):
                        pass
                if values:
                    n = len(values)
                    mean_val = sum(values) / n
                    if n > 1:
                        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
                        std_val = variance ** 0.5
                    else:
                        std_val = 0.0
                    numeric_stats[col["name"]] = {
                        "count": n,
                        "mean": mean_val,
                        "std": std_val,
                        "min": min(values),
                        "max": max(values)
                    }
        
        return {
            "name": meta.get("name"),
            "row_count": row_count,
            "column_count": len(columns),
            "columns": [{"name": c["name"], "type": c["dataType"]} for c in columns],
            "numeric_stats": numeric_stats
        }


# Convenience functions for quick usage
def get_asset_client() -> AssetClient:
    """Get an Asset Management client."""
    return AssetClient()

def get_testmonitor_client() -> TestMonitorClient:
    """Get a Test Monitor client."""
    return TestMonitorClient()

def get_notification_client() -> NotificationClient:
    """Get a Notification client."""
    return NotificationClient()

def get_dataframe_client() -> DataFrameClient:
    """Get a DataFrame (Data Tables) client."""
    return DataFrameClient()


if __name__ == "__main__":
    # Quick demo
    print("=== SystemLink Client Demo ===\n")
    
    # Enable logging to see API calls (optional - remove for production)
    # logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Using context manager (auto-closes session)
        with AssetClient() as assets:
            print("Asset Summary:", assets.summary())
            
            # Demo: iterate first 3 assets (memory-efficient)
            print("\nFirst 3 assets (via generator):")
            for i, asset in enumerate(assets.iter_all()):
                if i >= 3:
                    break
                print(f"  - {asset.get('name', 'Unknown')}")
        
        # Test Monitor summary
        with TestMonitorClient() as tm:
            print("\nTest Monitor Summary:", tm.summary(sample_size=100))
        
    except Exception as e:
        print(f"Error: {e}")
