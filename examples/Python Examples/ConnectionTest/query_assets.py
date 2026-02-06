"""
SystemLink Enterprise Asset Management Query Script

This script provides utilities to query and explore assets from the SystemLink
Asset Management API (niapm).

Usage:
    python query_assets.py                      # List all assets
    python query_assets.py --summary            # Show asset summary/statistics
    python query_assets.py --filter "modelName == 'PXI-4461'"
    python query_assets.py --calibratable       # Show only calibratable assets
    python query_assets.py --take 5             # Limit results

Environment variables (from .env file):
    SYSTEMLINK_API_URL  - The API server URL
    SYSTEMLINK_API_KEY  - Your API key
"""

import os
import sys
import json
import requests
import click
from typing import Dict, List, Optional
from datetime import datetime
from colorama import init, Fore, Style

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Initialize colorama
init()

# Environment variables
ENV_API_URL = "SYSTEMLINK_API_URL"
ENV_API_KEY = "SYSTEMLINK_API_KEY"


class AssetServiceClient:
    """Client for interacting with the SystemLink Asset Management API."""
    
    def __init__(self, base_url: str, api_key: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.headers = {
            "X-NI-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        json_body: Dict = None
    ) -> tuple:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_body,
                verify=self.verify_ssl,
                timeout=30
            )
            return response.status_code, response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            return 0, {"error": str(e)}
    
    def get_assets(
        self, 
        skip: int = 0, 
        take: int = 20,
        calibratable_only: bool = False,
        return_count: bool = True
    ) -> tuple:
        """Get assets with pagination."""
        params = {
            "Skip": skip,
            "Take": take,
            "CalibratableOnly": calibratable_only,
            "ReturnCount": return_count
        }
        return self._make_request("GET", "/niapm/v1/assets", params=params)
    
    def query_assets(
        self,
        filter_expr: str = None,
        skip: int = 0,
        take: int = 20,
        order_by: str = None,
        descending: bool = False,
        return_count: bool = True
    ) -> tuple:
        """Query assets with filter expression."""
        body = {
            "skip": skip,
            "take": take,
            "returnCount": return_count
        }
        if filter_expr:
            body["filter"] = filter_expr
        if order_by:
            body["orderBy"] = order_by
            body["descending"] = descending
        
        return self._make_request("POST", "/niapm/v1/query-assets", json_body=body)
    
    def get_asset_summary(self) -> tuple:
        """Get asset summary statistics."""
        return self._make_request("GET", "/niapm/v1/asset-summary")
    
    def get_asset_by_id(self, asset_id: str) -> tuple:
        """Get a specific asset by ID."""
        return self._make_request("GET", f"/niapm/v1/assets/{asset_id}")


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text: str):
    """Print error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text: str):
    """Print info message."""
    print(f"{Fore.YELLOW}→ {text}{Style.RESET_ALL}")


def format_date(date_str: str) -> str:
    """Format ISO date string to readable format."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return date_str


def display_asset_summary(summary: Dict):
    """Display asset summary in a formatted way."""
    print_header("Asset Summary")
    
    total = summary.get("totalAssetCount", 0)
    calibratable = summary.get("calibratableAssetCount", 0)
    
    print(f"  {'Total Assets:':<30} {Fore.WHITE}{total}{Style.RESET_ALL}")
    print(f"  {'Calibratable Assets:':<30} {Fore.WHITE}{calibratable}{Style.RESET_ALL}")
    
    # Calibration status breakdown
    cal_status = summary.get("calibrationStatus", {})
    if cal_status:
        print(f"\n  {Fore.CYAN}Calibration Status:{Style.RESET_ALL}")
        for status, count in cal_status.items():
            color = Fore.GREEN if status == "OK" else Fore.YELLOW if status == "APPROACHING" else Fore.RED
            print(f"    {status:<25} {color}{count}{Style.RESET_ALL}")
    
    # Location breakdown
    locations = summary.get("locationCounts", {})
    if locations:
        print(f"\n  {Fore.CYAN}Assets by Location:{Style.RESET_ALL}")
        for location, count in list(locations.items())[:10]:  # Show top 10
            print(f"    {location:<25} {count}")
        if len(locations) > 10:
            print(f"    ... and {len(locations) - 10} more locations")


def display_assets_table(assets: List[Dict], total_count: int = None):
    """Display assets in a table format."""
    if not assets:
        print_info("No assets found.")
        return
    
    if total_count:
        print_info(f"Showing {len(assets)} of {total_count} assets\n")
    
    # Table header
    print(f"{'ID':<40} {'Model':<20} {'Vendor':<15} {'Serial':<15} {'Location':<20}")
    print("-" * 110)
    
    for asset in assets:
        asset_id = asset.get("id", "N/A")[:38]
        model = (asset.get("modelName") or "N/A")[:18]
        vendor = (asset.get("vendorName") or "N/A")[:13]
        serial = (asset.get("serialNumber") or "N/A")[:13]
        location = (asset.get("location", {}).get("minionId") or "N/A")[:18]
        
        print(f"{asset_id:<40} {model:<20} {vendor:<15} {serial:<15} {location:<20}")


def display_asset_detail(asset: Dict):
    """Display detailed information for a single asset."""
    print_header(f"Asset: {asset.get('modelName', 'Unknown')}")
    
    fields = [
        ("ID", asset.get("id")),
        ("Model Name", asset.get("modelName")),
        ("Model Number", asset.get("modelNumber")),
        ("Vendor Name", asset.get("vendorName")),
        ("Vendor Number", asset.get("vendorNumber")),
        ("Serial Number", asset.get("serialNumber")),
        ("Asset Type", asset.get("assetType")),
        ("Is NI Asset", asset.get("isNIAsset")),
        ("Is System Controller", asset.get("isSystemController")),
        ("Firmware Version", asset.get("firmwareVersion")),
        ("Hardware Version", asset.get("hardwareVersion")),
        ("Bus Type", asset.get("busType")),
        ("Slot Number", asset.get("slotNumber")),
        ("Workspace", asset.get("workspace")),
        ("Last Updated", format_date(asset.get("lastUpdatedTimestamp"))),
    ]
    
    for label, value in fields:
        if value is not None:
            print(f"  {label + ':':<25} {Fore.WHITE}{value}{Style.RESET_ALL}")
    
    # Location info
    location = asset.get("location", {})
    if location:
        print(f"\n  {Fore.CYAN}Location:{Style.RESET_ALL}")
        print(f"    {'Minion ID:':<23} {location.get('minionId', 'N/A')}")
        print(f"    {'Physical Location:':<23} {location.get('physicalLocation', 'N/A')}")
        print(f"    {'State:':<23} {location.get('state', 'N/A')}")
    
    # Calibration info
    cal = asset.get("calibration", {})
    if cal:
        print(f"\n  {Fore.CYAN}Calibration:{Style.RESET_ALL}")
        print(f"    {'Is Calibratable:':<23} {cal.get('isCalibrationTracked', 'N/A')}")
        print(f"    {'Next Due:':<23} {format_date(cal.get('nextRecommendedDate'))}")
        print(f"    {'Status:':<23} {cal.get('recommendedStatus', 'N/A')}")
    
    # Custom properties
    props = asset.get("properties", {})
    if props:
        print(f"\n  {Fore.CYAN}Custom Properties:{Style.RESET_ALL}")
        for key, value in props.items():
            print(f"    {key + ':':<23} {value}")


@click.command()
@click.option("--server", default=None, help="The SystemLink API server URL")
@click.option("--api-key", default=None, help="The SystemLink API key")
@click.option("--summary", is_flag=True, help="Show asset summary statistics")
@click.option("--filter", "filter_expr", default=None, help='Filter expression (e.g., \'modelName == "PXI-4461"\')')
@click.option("--calibratable", is_flag=True, help="Show only calibratable assets")
@click.option("--skip", default=0, help="Number of assets to skip")
@click.option("--take", default=20, help="Number of assets to return")
@click.option("--asset-id", default=None, help="Get details for a specific asset ID")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def main(server, api_key, summary, filter_expr, calibratable, skip, take, asset_id, json_output):
    """
    Query and explore SystemLink Asset Management.
    
    Examples:
    
    \b
    # List all assets
    python query_assets.py
    
    \b
    # Show summary statistics
    python query_assets.py --summary
    
    \b
    # Filter by model name
    python query_assets.py --filter 'modelName == "PXI-4461"'
    
    \b
    # Show only calibratable assets
    python query_assets.py --calibratable
    
    \b
    # Get specific asset details
    python query_assets.py --asset-id "abc-123-xyz"
    """
    # Get configuration from environment or arguments
    server_url = server or os.getenv(ENV_API_URL)
    api_key_value = api_key or os.getenv(ENV_API_KEY)
    
    if not server_url:
        print_error(f"Server URL is required. Set {ENV_API_URL} or use --server")
        sys.exit(1)
    
    if not api_key_value:
        print_error(f"API key is required. Set {ENV_API_KEY} or use --api-key")
        sys.exit(1)
    
    # Create client
    client = AssetServiceClient(server_url, api_key_value)
    
    if not json_output:
        print_header("SystemLink Asset Management Explorer")
        print_info(f"Server: {server_url}")
    
    # Handle different operations
    if asset_id:
        # Get specific asset
        status, data = client.get_asset_by_id(asset_id)
        if status == 200:
            if json_output:
                print(json.dumps(data, indent=2))
            else:
                display_asset_detail(data)
        else:
            print_error(f"Failed to get asset: {data}")
            sys.exit(1)
    
    elif summary:
        # Get summary
        status, data = client.get_asset_summary()
        if status == 200:
            if json_output:
                print(json.dumps(data, indent=2))
            else:
                display_asset_summary(data)
        else:
            print_error(f"Failed to get summary: {data}")
            sys.exit(1)
    
    elif filter_expr:
        # Query with filter
        if not json_output:
            print_info(f"Filter: {filter_expr}")
        status, data = client.query_assets(
            filter_expr=filter_expr,
            skip=skip,
            take=take
        )
        if status == 200:
            if json_output:
                print(json.dumps(data, indent=2))
            else:
                assets = data.get("assets", [])
                total = data.get("totalCount")
                display_assets_table(assets, total)
        else:
            print_error(f"Failed to query assets: {data}")
            sys.exit(1)
    
    else:
        # List assets
        status, data = client.get_assets(
            skip=skip,
            take=take,
            calibratable_only=calibratable
        )
        if status == 200:
            if json_output:
                print(json.dumps(data, indent=2))
            else:
                assets = data.get("assets", [])
                total = data.get("totalCount")
                display_assets_table(assets, total)
        else:
            print_error(f"Failed to get assets: {data}")
            sys.exit(1)
    
    if not json_output:
        print()


if __name__ == "__main__":
    main()
