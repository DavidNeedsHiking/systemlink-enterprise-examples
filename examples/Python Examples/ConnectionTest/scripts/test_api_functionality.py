"""
SystemLink Enterprise API Basic Functionality Test

This script tests basic API functionality against the SystemLink Enterprise server
using various service endpoints to verify connectivity and authentication.

Usage:
    python test_api_functionality.py

    Or with command line options:
    python test_api_functionality.py --server <server_url> --api-key <api_key>

The script uses environment variables from .env file by default.
"""

import os
import sys
import json
import requests
import click
from typing import Tuple, Optional, Dict, Any, List
from colorama import init, Fore, Style
from datetime import datetime

# Load environment variables from .env file (check config/ folder first)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    # Check config/.env relative to this script's parent folder
    script_dir = Path(__file__).parent
    config_env = script_dir.parent / "config" / ".env"
    if config_env.exists():
        load_dotenv(config_env)
    else:
        load_dotenv()  # Default behavior
except ImportError:
    pass

# Initialize colorama for cross-platform colored output
init()

# Environment variable names
ENV_SERVER_URL = "SYSTEMLINK_API_URL"
ENV_API_KEY = "SYSTEMLINK_API_KEY"
ENV_SWAGGER_URL = "SYSTEMLINK_SWAGGER_URL"

# Default API server (the API testing endpoint)
DEFAULT_API_URL = "https://test-api.lifecyclesolutions.ni.com"


def print_header(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{Fore.CYAN}▶ {title}{Style.RESET_ALL}")
    print("-" * 40)


def print_success(message: str) -> None:
    """Print a success message with a checkmark."""
    print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {message}")


def print_failure(message: str) -> None:
    """Print a failure message with an X."""
    print(f"  {Fore.RED}✗{Style.RESET_ALL} {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  {Fore.BLUE}ℹ{Style.RESET_ALL} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"  {Fore.YELLOW}!{Style.RESET_ALL} {message}")


def print_json(data: Dict, indent: int = 4) -> None:
    """Print formatted JSON data."""
    formatted = json.dumps(data, indent=indent, default=str)
    for line in formatted.split('\n'):
        print(f"    {Fore.WHITE}{line}{Style.RESET_ALL}")


class SystemLinkAPITester:
    """Test class for SystemLink Enterprise API functionality."""
    
    def __init__(self, base_url: str, api_key: str, verify_ssl: bool = True, swagger_url: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.swagger_url = swagger_url
        self.headers = {
            "X-NI-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
        self.available_services = []
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict = None,
        params: Dict = None
    ) -> Tuple[bool, int, Any]:
        """
        Make an HTTP request to the API.
        
        Returns: (success, status_code, response_data)
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30,
                verify=self.verify_ssl
            )
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            success = response.status_code in [200, 201, 204]
            return success, response.status_code, response_data
            
        except requests.exceptions.RequestException as e:
            return False, 0, str(e)
    
    def discover_services_from_swagger(self) -> List[Dict]:
        """
        Discover available services from the Swagger/OpenAPI documentation URL.
        
        Returns a list of service info dictionaries.
        """
        if not self.swagger_url:
            return []
        
        print_subheader("Service Discovery (Swagger)")
        
        try:
            response = requests.get(
                self.swagger_url,
                timeout=10,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                print_success(f"Swagger documentation accessible")
                print_info(f"URL: {self.swagger_url}")
                
                # Try to parse service info from the HTML/JSON response
                content = response.text
                
                # Look for common service paths in the response
                services_found = []
                service_patterns = [
                    ("nialarm", "Alarm Service"),
                    ("niauth", "Authentication Service"),
                    ("nifile", "File Service"),
                    ("nitag", "Tag Service"),
                    ("nitestmonitor", "Test Monitor Service"),
                    ("nisysmgmt", "Systems Management Service"),
                    ("niasset", "Asset Service"),
                    ("nidashboard", "Dashboard Service"),
                    ("ninotebook", "Notebook Service"),
                    ("niworkorder", "Work Order Service"),
                ]
                
                for pattern, name in service_patterns:
                    if pattern in content.lower():
                        services_found.append({"path": pattern, "name": name})
                
                if services_found:
                    print_info(f"Discovered {len(services_found)} services:")
                    for svc in services_found:
                        print(f"      • {svc['name']} (/{svc['path']})")
                    self.available_services = services_found
                
                self.results["passed"] += 1
                return services_found
            else:
                print_warning(f"Swagger returned HTTP {response.status_code}")
                self.results["warnings"] += 1
                return []
                
        except requests.exceptions.RequestException as e:
            print_warning(f"Could not reach Swagger URL: {str(e)}")
            self.results["warnings"] += 1
            return []
    
    def test_api_info(self, service_path: str, service_name: str) -> bool:
        """Test getting API information for a service."""
        success, status, data = self._make_request("GET", f"/{service_path}")
        
        if success:
            print_success(f"{service_name} API is accessible")
            if isinstance(data, dict) and "version" in str(data).lower():
                print_info(f"Version info available")
            self.results["passed"] += 1
            return True
        else:
            print_failure(f"{service_name} API: HTTP {status}")
            self.results["failed"] += 1
            return False
    
    def test_auth_service(self) -> bool:
        """Test the authentication service."""
        print_subheader("Authentication Service")
        
        success, status, data = self._make_request("GET", "/niauth/v1/auth")
        
        if success:
            print_success("Authentication successful")
            if isinstance(data, dict):
                user = data.get("user", {})
                if user:
                    print_info(f"User ID: {user.get('userId', 'N/A')}")
                    print_info(f"Email: {user.get('email', 'N/A')}")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Authentication failed: Invalid API key")
            self.results["failed"] += 1
            return False
        else:
            print_failure(f"Authentication error: HTTP {status}")
            self.results["failed"] += 1
            return False
    
    def test_alarm_service(self) -> bool:
        """Test the Alarm Service API."""
        print_subheader("Alarm Service")
        
        # Test API info endpoint
        success, status, data = self._make_request("GET", "/nialarm")
        if success:
            print_success("Alarm service is accessible")
            self.results["passed"] += 1
        else:
            print_warning(f"Alarm service info: HTTP {status}")
            self.results["warnings"] += 1
        
        # Test querying alarms (empty query to just verify access)
        success, status, data = self._make_request(
            "POST", 
            "/nialarm/v1/query-instances",
            data={"skip": 0, "take": 1}
        )
        
        if success:
            print_success("Can query alarms")
            if isinstance(data, dict):
                total = data.get("totalCount", data.get("count", "unknown"))
                print_info(f"Total alarms in system: {total}")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Access denied to alarm service")
            self.results["failed"] += 1
            return False
        else:
            print_warning(f"Query alarms: HTTP {status}")
            self.results["warnings"] += 1
            return False
    
    def test_tag_service(self) -> bool:
        """Test the Tag Service API."""
        print_subheader("Tag Service")
        
        # Test getting tags
        success, status, data = self._make_request(
            "GET", 
            "/nitag/v2/tags",
            params={"take": 5}
        )
        
        if success:
            print_success("Tag service is accessible")
            if isinstance(data, dict):
                tags = data.get("tags", [])
                print_info(f"Retrieved {len(tags)} tags")
                if tags:
                    print_info(f"Sample tag: {tags[0].get('path', 'N/A')}")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Access denied to tag service")
            self.results["failed"] += 1
            return False
        else:
            print_warning(f"Tag service: HTTP {status}")
            self.results["warnings"] += 1
            return False
    
    def test_testmonitor_service(self) -> bool:
        """Test the Test Monitor Service API."""
        print_subheader("Test Monitor Service")
        
        # Test getting results
        success, status, data = self._make_request(
            "GET", 
            "/nitestmonitor/v2/results",
            params={"take": 5}
        )
        
        if success:
            print_success("Test Monitor service is accessible")
            if isinstance(data, dict):
                results = data.get("results", [])
                total = data.get("totalCount", len(results))
                print_info(f"Total test results: {total}")
                if results:
                    latest = results[0]
                    print_info(f"Latest result: {latest.get('programName', 'N/A')}")
                    print_info(f"Status: {latest.get('status', {}).get('statusType', 'N/A')}")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Access denied to Test Monitor service")
            self.results["failed"] += 1
            return False
        else:
            print_warning(f"Test Monitor service: HTTP {status}")
            self.results["warnings"] += 1
            return False
    
    def test_file_service(self) -> bool:
        """Test the File Service API."""
        print_subheader("File Service")
        
        # Test getting files
        success, status, data = self._make_request(
            "GET", 
            "/nifile/v1/service-groups/Default/files",
            params={"take": 5}
        )
        
        if success:
            print_success("File service is accessible")
            if isinstance(data, dict):
                files = data.get("availableFiles", [])
                print_info(f"Retrieved {len(files)} files")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Access denied to File service")
            self.results["failed"] += 1
            return False
        else:
            print_warning(f"File service: HTTP {status}")
            self.results["warnings"] += 1
            return False
    
    def test_systems_service(self) -> bool:
        """Test the Systems Management Service API."""
        print_subheader("Systems Management Service")
        
        # Test getting systems
        success, status, data = self._make_request(
            "GET", 
            "/nisysmgmt/v1/query-systems",
        )
        
        if not success:
            # Try POST method instead
            success, status, data = self._make_request(
                "POST", 
                "/nisysmgmt/v1/query-systems",
                data={"skip": 0, "take": 5}
            )
        
        if success:
            print_success("Systems Management service is accessible")
            if isinstance(data, dict):
                systems = data.get("data", [])
                total = data.get("totalCount", len(systems))
                print_info(f"Total systems: {total}")
            self.results["passed"] += 1
            return True
        elif status == 401:
            print_failure("Access denied to Systems Management service")
            self.results["failed"] += 1
            return False
        else:
            print_warning(f"Systems Management service: HTTP {status}")
            self.results["warnings"] += 1
            return False
    
    def run_all_tests(self) -> bool:
        """Run all API tests."""
        print_header("SystemLink Enterprise API Functionality Test")
        print(f"\nTarget: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.swagger_url:
            print(f"Swagger: {self.swagger_url}")
        
        if not self.verify_ssl:
            print_warning("SSL verification disabled")
        
        # Discover services from Swagger if URL is provided
        if self.swagger_url:
            self.discover_services_from_swagger()
        
        # Run tests
        auth_ok = self.test_auth_service()
        
        if not auth_ok:
            print_header("Test Summary")
            print_failure("Authentication failed - cannot proceed with other tests")
            print_info("Please verify your API key is correct and active")
            return False
        
        self.test_tag_service()
        self.test_testmonitor_service()
        self.test_file_service()
        self.test_alarm_service()
        self.test_systems_service()
        
        # Print summary
        print_header("Test Summary")
        total = self.results["passed"] + self.results["failed"] + self.results["warnings"]
        print(f"\n  Total tests:  {total}")
        print(f"  {Fore.GREEN}Passed:{Style.RESET_ALL}       {self.results['passed']}")
        print(f"  {Fore.RED}Failed:{Style.RESET_ALL}       {self.results['failed']}")
        print(f"  {Fore.YELLOW}Warnings:{Style.RESET_ALL}     {self.results['warnings']}")
        
        if self.results["failed"] == 0:
            print(f"\n{Fore.GREEN}All critical tests passed!{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}Some tests failed.{Style.RESET_ALL}")
            return False


@click.command()
@click.option(
    "--server",
    envvar=ENV_SERVER_URL,
    default=DEFAULT_API_URL,
    help=f"The SystemLink API server URL. Default: {DEFAULT_API_URL}"
)
@click.option(
    "--api-key",
    envvar=ENV_API_KEY,
    required=False,
    help=f"The SystemLink API key. Can also be set via {ENV_API_KEY} env var."
)
@click.option(
    "--swagger-url",
    envvar=ENV_SWAGGER_URL,
    required=False,
    help=f"The Swagger/OpenAPI documentation URL. Set via {ENV_SWAGGER_URL} env var."
)
@click.option(
    "--insecure",
    is_flag=True,
    default=False,
    help="Skip SSL certificate verification"
)
def main(server: str, api_key: str, swagger_url: str, insecure: bool) -> None:
    """
    Test basic API functionality against SystemLink Enterprise.
    
    Tests various service endpoints to verify connectivity, authentication,
    and basic read operations.
    """
    if not api_key:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} API key is required.")
        click.echo(f"Provide via --api-key option or {ENV_API_KEY} environment variable.")
        sys.exit(1)
    
    tester = SystemLinkAPITester(
        base_url=server,
        api_key=api_key,
        verify_ssl=not insecure,
        swagger_url=swagger_url
    )
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
