"""
SystemLink Enterprise API Client

A reusable Python wrapper for SystemLink REST APIs.
Supports: Asset Management, Test Monitor, Notification, and generic API calls.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise


class SystemLinkClient:
    """Base client for SystemLink Enterprise APIs."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        load_dotenv()
        self.base_url = (base_url or os.getenv("SYSTEMLINK_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("SYSTEMLINK_API_KEY", "")
        
        if not self.base_url or not self.api_key:
            raise ValueError("SYSTEMLINK_API_URL and SYSTEMLINK_API_KEY required")
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-NI-API-KEY": self.api_key,
            "Content-Type": "application/json"
        })

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET request to API endpoint."""
        resp = self.session.get(f"{self.base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """POST request to API endpoint."""
        resp = self.session.post(f"{self.base_url}{endpoint}", json=data)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def _delete(self, endpoint: str) -> bool:
        """DELETE request to API endpoint."""
        resp = self.session.delete(f"{self.base_url}{endpoint}")
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
        all_assets = []
        skip = 0
        while True:
            result = self.query(filter=filter, take=batch_size, skip=skip)
            assets = result.get("assets", [])
            all_assets.extend(assets)
            if len(assets) < batch_size:
                break
            skip += batch_size
        return all_assets

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
        result = self.query_results(filter=filter, take=min(batch_size, max_results))
        return result.get("results", [])

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
            take=limit,
            order_by="STARTED_AT_DESC"
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
                   cc: Optional[List[str]] = None, 
                   content_type: str = "text/plain") -> bool:
        """Send an email notification."""
        data = {
            "addressGroupDefinition": {
                "addresses": [{"type": "email", "value": addr} for addr in to]
            },
            "messageTemplateDefinition": {
                "subjectTemplate": subject,
                "bodyTemplate": body,
                "bodyType": content_type
            }
        }
        
        if cc:
            data["addressGroupDefinition"]["addresses"].extend(
                [{"type": "email", "value": addr, "cc": True} for addr in cc]
            )
        
        resp = self.session.post(
            f"{self.base_url}/ninotification/v1/apply-dynamic-strategy",
            json=data
        )
        return resp.status_code == 204

    def send_html_email(self, to: List[str], subject: str, html_body: str) -> bool:
        """Send an HTML email."""
        return self.send_email(to, subject, html_body, content_type="text/html")


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


if __name__ == "__main__":
    # Quick demo
    print("=== SystemLink Client Demo ===\n")
    
    try:
        # Asset summary
        assets = get_asset_client()
        print("Asset Summary:", assets.summary())
        
        # Test Monitor summary
        tm = get_testmonitor_client()
        print("\nTest Monitor Summary:", tm.summary(sample_size=100))
        
    except Exception as e:
        print(f"Error: {e}")
