"""
SystemLink Enterprise API Connection Test

This script tests the connection to a SystemLink Enterprise server by:
1. Checking if the server is reachable
2. Validating the API key authentication
3. Querying basic service information

Usage:
    python test_connection.py --server <server_url> --api-key <api_key>
    
    Or using environment variables:
    export SYSTEMLINK_SERVER_URL=https://my-systemlink-server.com
    export SYSTEMLINK_API_KEY=my-api-key
    python test_connection.py

Example:
    python test_connection.py --server https://my-systemlink-server.com --api-key my-api-key
"""

import os
import sys
import requests
import click
from typing import Tuple, Optional
from colorama import init, Fore, Style

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
    pass  # python-dotenv not installed, will use system env vars only

# Initialize colorama for cross-platform colored output
init()

# Environment variable names - prefer API URL, fallback to SERVER URL
ENV_API_URL = "SYSTEMLINK_API_URL"
ENV_SERVER_URL = "SYSTEMLINK_SERVER_URL"
ENV_API_KEY = "SYSTEMLINK_API_KEY"


def print_header(server_url: str) -> None:
    """Print the test header."""
    print("\n" + "=" * 60)
    print("SystemLink Enterprise Connection Test")
    print("=" * 60)
    print(f"\nTesting connection to: {server_url}")
    print("-" * 60 + "\n")


def print_success(message: str) -> None:
    """Print a success message with a checkmark."""
    print(f"{Fore.GREEN}[✓]{Style.RESET_ALL} {message}")


def print_failure(message: str) -> None:
    """Print a failure message with an X."""
    print(f"{Fore.RED}[✗]{Style.RESET_ALL} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {message}")


def test_server_reachable(server_url: str, verify_ssl: bool = True) -> Tuple[bool, str]:
    """
    Test if the server is reachable.
    
    :param server_url: The SystemLink server URL.
    :param verify_ssl: Whether to verify SSL certificates.
    :return: Tuple of (success, message).
    """
    try:
        response = requests.get(
            f"{server_url}/niauth/v1/auth", 
            timeout=10,
            verify=verify_ssl
        )
        # Even a 401 means the server is reachable
        return True, "Server is reachable"
    except requests.exceptions.SSLError as e:
        return False, f"SSL Certificate Error: {str(e)}"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection Error: Unable to reach server at {server_url}"
    except requests.exceptions.Timeout:
        return False, "Connection Timeout: Server did not respond within 10 seconds"
    except requests.exceptions.RequestException as e:
        return False, f"Request Error: {str(e)}"


def test_authentication(server_url: str, api_key: str, verify_ssl: bool = True) -> Tuple[bool, str, Optional[dict]]:
    """
    Test if the API key is valid by querying the auth endpoint.
    
    :param server_url: The SystemLink server URL.
    :param api_key: The API key to validate.
    :param verify_ssl: Whether to verify SSL certificates.
    :return: Tuple of (success, message, user_info).
    """
    headers = {"X-NI-API-KEY": api_key}
    
    try:
        response = requests.get(
            f"{server_url}/niauth/v1/auth",
            headers=headers,
            timeout=10,
            verify=verify_ssl
        )
        
        if response.status_code == 200:
            user_info = response.json()
            return True, "API authentication successful", user_info
        elif response.status_code == 401:
            return False, "Authentication failed: Invalid or expired API key", None
        elif response.status_code == 403:
            return False, "Authentication failed: Insufficient permissions", None
        else:
            return False, f"Authentication failed: HTTP {response.status_code}", None
            
    except requests.exceptions.RequestException as e:
        return False, f"Authentication request failed: {str(e)}", None


def test_service_availability(
    server_url: str, 
    api_key: str, 
    service_name: str,
    service_route: str,
    verify_ssl: bool = True
) -> Tuple[bool, str]:
    """
    Test if a specific SystemLink service is available.
    
    :param server_url: The SystemLink server URL.
    :param api_key: The API key.
    :param service_name: The display name of the service.
    :param service_route: The API route to test.
    :param verify_ssl: Whether to verify SSL certificates.
    :return: Tuple of (success, message).
    """
    headers = {"X-NI-API-KEY": api_key}
    
    try:
        response = requests.get(
            f"{server_url}/{service_route}",
            headers=headers,
            timeout=10,
            verify=verify_ssl
        )
        
        if response.status_code in [200, 204]:
            return True, f"{service_name}: Available"
        elif response.status_code == 401:
            return False, f"{service_name}: Authentication required"
        elif response.status_code == 403:
            return False, f"{service_name}: Access denied"
        elif response.status_code == 404:
            return False, f"{service_name}: Service not found"
        else:
            return False, f"{service_name}: HTTP {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        return False, f"{service_name}: Request failed - {str(e)}"


def run_connection_tests(server_url: str, api_key: str, insecure: bool = False) -> bool:
    """
    Run all connection tests.
    
    :param server_url: The SystemLink server URL.
    :param api_key: The API key.
    :param insecure: Whether to skip SSL verification.
    :return: True if all tests pass, False otherwise.
    """
    verify_ssl = not insecure
    all_passed = True
    
    print_header(server_url)
    
    if insecure:
        print_warning("SSL certificate verification is disabled\n")
    
    # Test 1: Server reachability
    success, message = test_server_reachable(server_url, verify_ssl)
    if success:
        print_success(message)
    else:
        print_failure(message)
        print("\n" + "=" * 60)
        print(f"{Fore.RED}Connection test failed!{Style.RESET_ALL}")
        print("=" * 60 + "\n")
        return False
    
    # Test 2: API Authentication
    success, message, user_info = test_authentication(server_url, api_key, verify_ssl)
    if success:
        print_success(message)
        if user_info:
            # Try to extract user identifier from response
            user_id = user_info.get("user", {}).get("email") or \
                     user_info.get("user", {}).get("userId") or \
                     user_info.get("userId") or \
                     "Unknown"
            if user_id != "Unknown":
                print_success(f"User: {user_id}")
    else:
        print_failure(message)
        all_passed = False
    
    # Test 3: Service availability checks
    services = [
        ("Test Monitor Service", "nitestmonitor/v2/results?take=1"),
        ("File Service", "nifile/v1/service-groups/Default/files?take=1"),
        ("Tag Service", "nitag/v2/tags?take=1"),
    ]
    
    for service_name, service_route in services:
        success, message = test_service_availability(
            server_url, api_key, service_name, service_route, verify_ssl
        )
        if success:
            print_success(message)
        else:
            print_warning(message)
            # Service unavailability is a warning, not a failure
    
    # Print summary
    print("\n" + "=" * 60)
    if all_passed:
        print(f"{Fore.GREEN}Connection test completed successfully!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Connection test completed with errors.{Style.RESET_ALL}")
    print("=" * 60 + "\n")
    
    return all_passed


@click.command()
@click.option(
    "--server",
    required=False,
    help=f"The SystemLink Enterprise API URL. Can also be set via {ENV_API_URL} or {ENV_SERVER_URL} env var."
)
@click.option(
    "--api-key",
    envvar=ENV_API_KEY,
    required=False,
    help=f"The SystemLink API key. Can also be set via {ENV_API_KEY} env var."
)
@click.option(
    "--insecure",
    is_flag=True,
    default=False,
    help="Skip SSL certificate verification (not recommended for production)"
)
def main(server: str, api_key: str, insecure: bool) -> None:
    """
    Test the connection to a SystemLink Enterprise server.
    
    Credentials can be provided via command line options or environment variables:
    
    \b
    Environment variables:
      SYSTEMLINK_API_URL     - The API server URL (preferred)
      SYSTEMLINK_SERVER_URL  - The server URL (fallback)
      SYSTEMLINK_API_KEY     - Your API key
    
    Command line options take precedence over environment variables.
    """
    # Get server URL: CLI option > API_URL env > SERVER_URL env
    if not server:
        server = os.getenv(ENV_API_URL) or os.getenv(ENV_SERVER_URL)
    
    # Validate required parameters
    if not server:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} Server URL is required.")
        click.echo(f"Provide via --server option or {ENV_API_URL}/{ENV_SERVER_URL} environment variable.")
        sys.exit(1)
    
    if not api_key:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} API key is required.")
        click.echo(f"Provide via --api-key option or {ENV_API_KEY} environment variable.")
        sys.exit(1)
    
    # Remove trailing slash from server URL if present
    server_url = server.rstrip("/")
    
    success = run_connection_tests(server_url, api_key, insecure)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
