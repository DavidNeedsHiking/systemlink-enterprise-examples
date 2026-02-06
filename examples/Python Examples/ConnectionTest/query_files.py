"""
SystemLink Enterprise File Service Query Script

This script provides utilities to query and list files from the SystemLink
File Service API, with filtering by workspace, name, and other properties.

Usage:
    python query_files.py --workspace "Data Science"
    python query_files.py --workspace-id ee940aa2-05d3-4585-a822-52f7234a5207
    python query_files.py --name "anomaly_report.json"
    python query_files.py --list-workspaces

Environment variables (from .env file):
    SYSTEMLINK_API_URL  - The API server URL
    SYSTEMLINK_API_KEY  - Your API key
"""

import os
import sys
import json
import requests
import click
from typing import Dict, List, Optional, Tuple
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


class FileServiceClient:
    """Client for interacting with the SystemLink File Service API."""
    
    def __init__(self, base_url: str, api_key: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.headers = {
            "X-NI-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self._workspace_cache: Dict[str, str] = {}
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        data: Dict = None
    ) -> Tuple[bool, int, any]:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30,
                verify=self.verify_ssl
            )
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return response.status_code in [200, 201, 204], response.status_code, response_data
            
        except requests.exceptions.RequestException as e:
            return False, 0, str(e)
    
    def get_workspaces(self) -> List[Dict]:
        """
        Get list of workspaces by inferring from file data.
        Note: The workspace API may not be directly available, so we extract
        unique workspace IDs from file metadata.
        """
        success, status, data = self._make_request(
            "GET",
            "/nifile/v1/service-groups/Default/files",
            params={"take": 500}
        )
        
        if not success:
            return []
        
        files = data.get("availableFiles", [])
        workspaces = {}
        
        for f in files:
            ws_id = f.get("workspace")
            if ws_id and ws_id not in workspaces:
                workspaces[ws_id] = {
                    "id": ws_id,
                    "name": ws_id,  # We don't have the name from file API
                    "fileCount": 0
                }
            if ws_id:
                workspaces[ws_id]["fileCount"] += 1
        
        return list(workspaces.values())
    
    def get_files(
        self,
        workspace_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        take: int = 200,
        skip: int = 0
    ) -> List[Dict]:
        """
        Get files from the File Service.
        
        Args:
            workspace_id: Filter by workspace ID
            name_filter: Filter by file name (partial match)
            take: Maximum number of files to return
            skip: Number of files to skip (for pagination)
        
        Returns:
            List of file dictionaries
        """
        success, status, data = self._make_request(
            "GET",
            "/nifile/v1/service-groups/Default/files",
            params={"take": take, "skip": skip}
        )
        
        if not success:
            print(f"{Fore.RED}Error fetching files: HTTP {status}{Style.RESET_ALL}")
            return []
        
        files = data.get("availableFiles", [])
        
        # Apply filters
        if workspace_id:
            files = [f for f in files if f.get("workspace") == workspace_id]
        
        if name_filter:
            name_lower = name_filter.lower()
            files = [
                f for f in files 
                if name_lower in f.get("properties", {}).get("Name", "").lower()
            ]
        
        return files
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Get a specific file by its ID."""
        # First try direct endpoint
        success, status, data = self._make_request(
            "GET",
            f"/nifile/v1/service-groups/Default/files/{file_id}"
        )
        
        if success:
            return data
        
        # Fallback: search in all files
        files = self.get_files(take=500)
        for f in files:
            if f.get("id") == file_id:
                return f
        
        return None
    
    def download_file_content(self, file_id: str) -> Optional[bytes]:
        """Download the content of a file."""
        url = f"{self.base_url}/nifile/v1/service-groups/Default/files/{file_id}/data"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=60,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                return response.content
            return None
            
        except requests.exceptions.RequestException:
            return None


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_timestamp


def print_file_table(files: List[Dict], show_workspace: bool = True) -> None:
    """Print files in a formatted table."""
    if not files:
        print(f"{Fore.YELLOW}No files found.{Style.RESET_ALL}")
        return
    
    # Header
    if show_workspace:
        print(f"\n{'Name':<45} {'Created':<20} {'Size':>10} {'Workspace':<36}")
        print("-" * 115)
    else:
        print(f"\n{'Name':<50} {'Created':<20} {'Size':>12}")
        print("-" * 85)
    
    # Sort by created date (newest first)
    sorted_files = sorted(
        files, 
        key=lambda x: x.get("created", ""), 
        reverse=True
    )
    
    for f in sorted_files:
        name = f.get("properties", {}).get("Name", "Unknown")
        created = format_timestamp(f.get("created", "N/A"))
        size = format_size(f.get("size", 0))
        workspace = f.get("workspace", "N/A")
        
        # Truncate name if too long
        if show_workspace:
            display_name = name[:43] + ".." if len(name) > 45 else name
            print(f"{display_name:<45} {created:<20} {size:>10} {workspace:<36}")
        else:
            display_name = name[:48] + ".." if len(name) > 50 else name
            print(f"{display_name:<50} {created:<20} {size:>12}")


def print_file_details(file: Dict) -> None:
    """Print detailed information about a file."""
    print(f"\n{Fore.CYAN}File Details{Style.RESET_ALL}")
    print("-" * 40)
    
    props = file.get("properties", {})
    
    print(f"  {'Name:':<15} {props.get('Name', 'Unknown')}")
    print(f"  {'ID:':<15} {file.get('id', 'N/A')}")
    print(f"  {'Created:':<15} {format_timestamp(file.get('created', 'N/A'))}")
    print(f"  {'Size:':<15} {format_size(file.get('size', 0))}")
    print(f"  {'Workspace:':<15} {file.get('workspace', 'N/A')}")
    print(f"  {'Service Group:':<15} {file.get('serviceGroup', 'N/A')}")
    
    # Print custom properties
    custom_props = {k: v for k, v in props.items() if k != "Name"}
    if custom_props:
        print(f"\n  {Fore.CYAN}Custom Properties:{Style.RESET_ALL}")
        for key, value in custom_props.items():
            print(f"    {key}: {value}")
    
    # Print links
    links = file.get("_links", {})
    if links:
        print(f"\n  {Fore.CYAN}API Links:{Style.RESET_ALL}")
        for link_name, link_data in links.items():
            print(f"    {link_name}: {link_data.get('href', 'N/A')}")


@click.command()
@click.option(
    "--server",
    envvar=ENV_API_URL,
    help="The SystemLink API server URL"
)
@click.option(
    "--api-key",
    envvar=ENV_API_KEY,
    help="The SystemLink API key"
)
@click.option(
    "--workspace", "-w",
    help="Filter by workspace name (partial match supported)"
)
@click.option(
    "--workspace-id", "-wid",
    help="Filter by workspace ID (exact match)"
)
@click.option(
    "--name", "-n",
    help="Filter by file name (partial match)"
)
@click.option(
    "--file-id", "-id",
    help="Get details for a specific file by ID"
)
@click.option(
    "--list-workspaces", "-lw",
    is_flag=True,
    help="List all available workspaces"
)
@click.option(
    "--limit", "-l",
    default=50,
    help="Maximum number of files to display (default: 50)"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table or json)"
)
@click.option(
    "--download", "-d",
    help="Download file to specified path (requires --file-id)"
)
@click.option(
    "--insecure",
    is_flag=True,
    help="Skip SSL verification"
)
def main(
    server: str,
    api_key: str,
    workspace: str,
    workspace_id: str,
    name: str,
    file_id: str,
    list_workspaces: bool,
    limit: int,
    output: str,
    download: str,
    insecure: bool
) -> None:
    """
    Query files from SystemLink Enterprise File Service.
    
    Examples:
    
    \b
    List files in a workspace:
        python query_files.py --workspace-id ee940aa2-...
    
    \b
    Search for files by name:
        python query_files.py --name "anomaly_report"
    
    \b
    Get file details:
        python query_files.py --file-id 58cdfc9e-...
    
    \b
    Export as JSON:
        python query_files.py --workspace-id ... --output json > files.json
    """
    # Validate required parameters
    if not server:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Server URL is required.")
        click.echo(f"Set via --server or {ENV_API_URL} environment variable.")
        sys.exit(1)
    
    if not api_key:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} API key is required.")
        click.echo(f"Set via --api-key or {ENV_API_KEY} environment variable.")
        sys.exit(1)
    
    # Create client
    client = FileServiceClient(
        base_url=server,
        api_key=api_key,
        verify_ssl=not insecure
    )
    
    # List workspaces
    if list_workspaces:
        print(f"\n{Fore.CYAN}Available Workspaces{Style.RESET_ALL}")
        print("=" * 60)
        
        workspaces = client.get_workspaces()
        
        if output == "json":
            print(json.dumps(workspaces, indent=2))
        else:
            print(f"\n{'Workspace ID':<40} {'Files':>10}")
            print("-" * 52)
            for ws in sorted(workspaces, key=lambda x: x["fileCount"], reverse=True):
                print(f"{ws['id']:<40} {ws['fileCount']:>10}")
        
        print(f"\n{Fore.GREEN}Total workspaces: {len(workspaces)}{Style.RESET_ALL}")
        return
    
    # Get specific file by ID
    if file_id:
        file = client.get_file_by_id(file_id)
        
        if file:
            if download:
                print(f"Downloading file to {download}...")
                content = client.download_file_content(file_id)
                if content:
                    with open(download, 'wb') as f:
                        f.write(content)
                    print(f"{Fore.GREEN}Downloaded successfully ({format_size(len(content))}){Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Failed to download file.{Style.RESET_ALL}")
                    sys.exit(1)
            elif output == "json":
                print(json.dumps(file, indent=2))
            else:
                print_file_details(file)
        else:
            print(f"{Fore.RED}File not found: {file_id}{Style.RESET_ALL}")
            sys.exit(1)
        return
    
    # Query files
    print(f"\n{Fore.CYAN}SystemLink File Service Query{Style.RESET_ALL}")
    print("=" * 60)
    print(f"Server: {server}")
    
    if workspace_id:
        print(f"Workspace ID: {workspace_id}")
    if name:
        print(f"Name filter: {name}")
    
    files = client.get_files(
        workspace_id=workspace_id,
        name_filter=name,
        take=500  # Get more to filter
    )
    
    # Limit results for display
    display_files = files[:limit]
    
    if output == "json":
        print(json.dumps(display_files, indent=2, default=str))
    else:
        print(f"\n{Fore.GREEN}Found {len(files)} files{Style.RESET_ALL}")
        if len(files) > limit:
            print(f"{Fore.YELLOW}(Showing first {limit}, use --limit to show more){Style.RESET_ALL}")
        
        print_file_table(display_files, show_workspace=not workspace_id)
        
        # Summary
        total_size = sum(f.get("size", 0) for f in files)
        print(f"\n{Fore.CYAN}Summary:{Style.RESET_ALL}")
        print(f"  Total files: {len(files)}")
        print(f"  Total size: {format_size(total_size)}")


if __name__ == "__main__":
    main()
