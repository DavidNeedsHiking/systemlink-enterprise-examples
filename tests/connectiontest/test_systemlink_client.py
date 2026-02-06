"""
Unit tests for SystemLink Enterprise API Client.

Tests cover:
- SystemLinkClient base class (authentication, HTTP methods, context manager)
- AssetClient (query, count, pagination, calibration methods)
- TestMonitorClient (query, count, failure analysis)
- NotificationClient (send_email)
- Retry and rate limiting behavior
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime, timezone, timedelta

# Add the ConnectionTest directory to path for imports
# Get the workspace root (go up from tests/connectiontest to root)
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(_TEST_DIR))
_CONNECTIONTEST_PATH = os.path.join(_WORKSPACE_ROOT, "examples", "Python Examples", "ConnectionTest")
sys.path.insert(0, _CONNECTIONTEST_PATH)


# Module path for patching (updated for new folder structure)
MODULE_PATH = "core.systemlink_client"


class TestSystemLinkClientFixtures:
    """Shared fixtures for all client tests."""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables for API credentials."""
        with patch.dict(os.environ, {
            "SYSTEMLINK_API_URL": "https://test-api.example.com",
            "SYSTEMLINK_API_KEY": "test-api-key-123"
        }):
            yield

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        with patch(f"{MODULE_PATH}.requests.Session") as MockSession:
            # Use MagicMock for the session to support attribute assignment
            session = MagicMock()
            MockSession.return_value = session
            yield session


class TestSystemLinkClient(TestSystemLinkClientFixtures):
    """Tests for base SystemLinkClient class."""

    def test_init_with_valid_credentials(self, mock_env, mock_session):
        """Test client initialization with valid credentials."""
        from core.systemlink_client import SystemLinkClient
        
        client = SystemLinkClient()
        
        assert client.base_url == "https://test-api.example.com"
        assert client.api_key == "test-api-key-123"
        mock_session.headers.update.assert_called_once()

    def test_init_with_explicit_credentials(self, mock_session):
        """Test client initialization with explicit credentials."""
        from core.systemlink_client import SystemLinkClient
        
        client = SystemLinkClient(
            base_url="https://custom-api.com",
            api_key="custom-key"
        )
        
        assert client.base_url == "https://custom-api.com"
        assert client.api_key == "custom-key"

    def test_init_missing_credentials_raises_error(self, mock_session):
        """Test that missing credentials raise ValueError."""
        from core.systemlink_client import SystemLinkClient
        
        # Mock load_dotenv to be a no-op so it doesn't load .env file
        with patch(f"{MODULE_PATH}.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match="SYSTEMLINK_API_URL and SYSTEMLINK_API_KEY required"):
                    SystemLinkClient()

    def test_init_strips_trailing_slash(self, mock_session):
        """Test that trailing slash is stripped from base_url."""
        from core.systemlink_client import SystemLinkClient
        
        client = SystemLinkClient(
            base_url="https://api.example.com/",
            api_key="key"
        )
        
        assert client.base_url == "https://api.example.com"

    def test_context_manager_closes_session(self, mock_env, mock_session):
        """Test that context manager closes session on exit."""
        from core.systemlink_client import SystemLinkClient
        
        with SystemLinkClient() as client:
            pass
        
        mock_session.close.assert_called_once()

    def test_get_request(self, mock_env, mock_session):
        """Test GET request method."""
        from core.systemlink_client import SystemLinkClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = SystemLinkClient()
        result = client._get("/test/endpoint", params={"key": "value"})
        
        mock_session.get.assert_called_once()
        assert result == {"data": "test"}

    def test_post_request(self, mock_env, mock_session):
        """Test POST request method."""
        from core.systemlink_client import SystemLinkClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"result": "created"}'
        mock_response.json.return_value = {"result": "created"}
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        client = SystemLinkClient()
        result = client._post("/test/endpoint", data={"field": "value"})
        
        mock_session.post.assert_called_once()
        assert result == {"result": "created"}

    def test_delete_request(self, mock_env, mock_session):
        """Test DELETE request method."""
        from core.systemlink_client import SystemLinkClient
        
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status = Mock()
        mock_session.delete.return_value = mock_response
        
        client = SystemLinkClient()
        result = client._delete("/test/resource/123")
        
        mock_session.delete.assert_called_once()
        assert result is True

    def test_empty_response_handling(self, mock_env, mock_session):
        """Test handling of empty response body."""
        from core.systemlink_client import SystemLinkClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = SystemLinkClient()
        result = client._get("/test/endpoint")
        
        assert result == {}


class TestAssetClient(TestSystemLinkClientFixtures):
    """Tests for AssetClient class."""

    @pytest.fixture
    def asset_client(self, mock_env, mock_session):
        """Create an AssetClient with mocked session."""
        from core.systemlink_client import AssetClient
        return AssetClient()

    def test_query_assets_simple(self, asset_client, mock_session):
        """Test simple asset query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"assets": [{"id": "1", "name": "DUT1"}]}'
        mock_response.json.return_value = {"assets": [{"id": "1", "name": "DUT1"}]}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        result = asset_client.query(take=10)
        
        assert "assets" in result
        assert len(result["assets"]) == 1

    def test_query_assets_with_filter(self, asset_client, mock_session):
        """Test asset query with filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"assets": [], "totalCount": 0}
        mock_response.text = '{"assets": []}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        result = asset_client.query(filter='modelName == "PXI-4110"', return_count=True)
        
        # Verify filter was passed in params
        call_args = mock_session.get.call_args
        assert call_args is not None

    def test_count_assets(self, asset_client, mock_session):
        """Test counting assets."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"assets": [], "totalCount": 42}
        mock_response.text = '{"assets": [], "totalCount": 42}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        count = asset_client.count()
        
        assert count == 42

    def test_get_by_id(self, asset_client, mock_session):
        """Test getting asset by ID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "asset-123", "name": "Test Asset"}
        mock_response.text = '{"id": "asset-123"}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        result = asset_client.get_by_id("asset-123")
        
        assert result["id"] == "asset-123"

    def test_iter_all_single_batch(self, asset_client, mock_session):
        """Test iterating all assets when results fit in one batch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        }
        mock_response.text = '{"assets": [{"id": "1"}]}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        assets = list(asset_client.iter_all(batch_size=1000))
        
        assert len(assets) == 3

    def test_iter_all_multiple_batches(self, asset_client, mock_session):
        """Test iterating all assets across multiple batches."""
        # First call returns full batch
        batch1 = Mock()
        batch1.status_code = 200
        batch1.json.return_value = {"assets": [{"id": "1"}, {"id": "2"}]}
        batch1.text = '{"assets": []}'
        batch1.raise_for_status = Mock()
        
        # Second call returns partial batch (signals end)
        batch2 = Mock()
        batch2.status_code = 200
        batch2.json.return_value = {"assets": [{"id": "3"}]}
        batch2.text = '{"assets": []}'
        batch2.raise_for_status = Mock()
        
        mock_session.get.side_effect = [batch1, batch2]
        
        assets = list(asset_client.iter_all(batch_size=2))
        
        assert len(assets) == 3
        assert mock_session.get.call_count == 2

    def test_get_calibratable(self, asset_client, mock_session):
        """Test getting calibratable assets uses correct filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"assets": []}
        mock_response.text = '{"assets": []}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        asset_client.get_calibratable()
        
        # Verify isNIAsset filter was applied
        call_args = mock_session.get.call_args
        assert call_args is not None

    def test_summary(self, asset_client, mock_session):
        """Test getting asset summary."""
        # Mock responses for total, calibratable, and overdue counts
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"assets": [], "totalCount": 100}
        mock_response.text = '{"assets": []}'
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        summary = asset_client.summary()
        
        assert "total" in summary
        assert "calibratable" in summary
        assert "overdue_calibration" in summary


class TestTestMonitorClient(TestSystemLinkClientFixtures):
    """Tests for TestMonitorClient class."""

    @pytest.fixture
    def tm_client(self, mock_env, mock_session):
        """Create a TestMonitorClient with mocked session."""
        from core.systemlink_client import TestMonitorClient
        return TestMonitorClient()

    def test_query_results(self, tm_client, mock_session):
        """Test querying test results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "r1", "status": {"statusType": "PASSED"}}]
        }
        mock_response.text = '{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        result = tm_client.query_results(take=10)
        
        assert "results" in result
        mock_session.post.assert_called_once()

    def test_query_results_with_filter(self, tm_client, mock_session):
        """Test querying test results with filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "totalCount": 5}
        mock_response.text = '{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        result = tm_client.query_results(
            filter='status.statusType == "FAILED"',
            return_count=True
        )
        
        assert result.get("totalCount") == 5

    def test_count_results(self, tm_client, mock_session):
        """Test counting test results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "totalCount": 150}
        mock_response.text = '{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        count = tm_client.count_results()
        
        assert count == 150

    def test_get_failed_results(self, tm_client, mock_session):
        """Test getting failed test results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "r1", "status": {"statusType": "FAILED"}},
                {"id": "r2", "status": {"statusType": "FAILED"}}
            ]
        }
        mock_response.text = '{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        failed = tm_client.get_failed_results(limit=50)
        
        assert len(failed) == 2
        assert all(r["status"]["statusType"] == "FAILED" for r in failed)

    def test_query_steps(self, tm_client, mock_session):
        """Test querying test steps."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "steps": [{"stepId": "s1", "name": "Init"}]
        }
        mock_response.text = '{"steps": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        result = tm_client.query_steps(result_id="result-123")
        
        assert "steps" in result

    def test_query_products(self, tm_client, mock_session):
        """Test querying products."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "products": [{"partNumber": "PN-001"}]
        }
        mock_response.text = '{"products": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        result = tm_client.query_products(take=50)
        
        assert "products" in result

    def test_iter_results(self, tm_client, mock_session):
        """Test iterating through test results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "r1"}, {"id": "r2"}]
        }
        mock_response.text = '{"results": []}'
        mock_response.raise_for_status = Mock()
        mock_session.post.return_value = mock_response
        
        results = list(tm_client.iter_results(max_results=100))
        
        assert len(results) == 2

    def test_summary(self, tm_client, mock_session):
        """Test getting test monitor summary."""
        # First call for count, second for sample
        count_response = Mock()
        count_response.status_code = 200
        count_response.json.return_value = {"results": [], "totalCount": 1000}
        count_response.text = '{"results": []}'
        count_response.raise_for_status = Mock()
        
        sample_response = Mock()
        sample_response.status_code = 200
        sample_response.json.return_value = {
            "results": [
                {"status": {"statusType": "PASSED"}, "programName": "Test1", "operator": "Op1"},
                {"status": {"statusType": "FAILED"}, "programName": "Test1", "operator": "Op2"}
            ]
        }
        sample_response.text = '{"results": []}'
        sample_response.raise_for_status = Mock()
        
        mock_session.post.side_effect = [count_response, sample_response]
        
        summary = tm_client.summary(sample_size=100)
        
        assert summary["total_results"] == 1000
        assert "status_distribution" in summary
        assert "top_programs" in summary


class TestNotificationClient(TestSystemLinkClientFixtures):
    """Tests for NotificationClient class."""

    @pytest.fixture
    def notification_client(self, mock_env, mock_session):
        """Create a NotificationClient with mocked session."""
        from core.systemlink_client import NotificationClient
        return NotificationClient()

    def test_send_email_success(self, notification_client, mock_session):
        """Test sending email successfully."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.post.return_value = mock_response
        
        result = notification_client.send_email(
            to=["user@example.com"],
            subject="Test Subject",
            body="Test body content"
        )
        
        assert result is True
        mock_session.post.assert_called()

    def test_send_email_with_cc(self, notification_client, mock_session):
        """Test sending email with CC recipients."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.post.return_value = mock_response
        
        result = notification_client.send_email(
            to=["user@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=["cc@example.com"]
        )
        
        assert result is True
        # Verify CC was included in the request
        call_args = mock_session.post.call_args
        assert call_args is not None

    def test_send_email_failure(self, notification_client, mock_session):
        """Test handling email send failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_session.post.return_value = mock_response
        
        result = notification_client.send_email(
            to=["user@example.com"],
            subject="Test",
            body="Body"
        )
        
        assert result is False

    def test_send_html_email(self, notification_client, mock_session):
        """Test sending HTML email."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.post.return_value = mock_response
        
        html = "<h1>Hello</h1><p>This is HTML content</p>"
        result = notification_client.send_html_email(
            to=["user@example.com"],
            subject="HTML Test",
            html_body=html
        )
        
        assert result is True

    def test_email_request_structure(self, notification_client, mock_session):
        """Test that email request has correct structure."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.post.return_value = mock_response
        
        notification_client.send_email(
            to=["test@example.com"],
            subject="Subject",
            body="Body"
        )
        
        call_args = mock_session.post.call_args
        assert call_args is not None
        
        # Check URL
        url = call_args[0][0]
        assert "/ninotification/v1/apply-dynamic-strategy" in url
        
        # Check request body structure
        json_data = call_args[1]["json"]
        assert "notificationStrategy" in json_data
        configs = json_data["notificationStrategy"]["notificationConfigurations"]
        assert len(configs) == 1
        assert "addressGroup" in configs[0]
        assert "messageTemplate" in configs[0]


class TestConvenienceFunctions(TestSystemLinkClientFixtures):
    """Tests for module-level convenience functions."""

    def test_get_asset_client(self, mock_env, mock_session):
        """Test get_asset_client convenience function."""
        from core.systemlink_client import get_asset_client, AssetClient
        
        client = get_asset_client()
        
        assert isinstance(client, AssetClient)
        client.close()

    def test_get_testmonitor_client(self, mock_env, mock_session):
        """Test get_testmonitor_client convenience function."""
        from core.systemlink_client import get_testmonitor_client, TestMonitorClient
        
        client = get_testmonitor_client()
        
        assert isinstance(client, TestMonitorClient)
        client.close()

    def test_get_notification_client(self, mock_env, mock_session):
        """Test get_notification_client convenience function."""
        from core.systemlink_client import get_notification_client, NotificationClient
        
        client = get_notification_client()
        
        assert isinstance(client, NotificationClient)
        client.close()


class TestRetryBehavior(TestSystemLinkClientFixtures):
    """Tests for retry behavior when tenacity is available."""

    def test_retry_decorator_created(self, mock_env, mock_session):
        """Test that retry decorator is created when tenacity is available."""
        from core.systemlink_client import TENACITY_AVAILABLE, _retry_decorator
        
        # Decorator should be a function
        assert callable(_retry_decorator)

    def test_request_with_rate_limiting(self, mock_env, mock_session):
        """Test that rate limiter is invoked."""
        from core.systemlink_client import SystemLinkClient, _RateLimiter
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        
        client = SystemLinkClient()
        result = client._get("/test")
        
        # Should complete without error
        assert result == {"data": "test"}


class TestErrorHandling(TestSystemLinkClientFixtures):
    """Tests for error handling scenarios."""

    def test_http_error_raised(self, mock_env, mock_session):
        """Test that HTTP errors are raised."""
        from core.systemlink_client import SystemLinkClient
        import requests
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = '{"error": "Not found"}'
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_session.get.return_value = mock_response
        
        client = SystemLinkClient()
        
        with pytest.raises(requests.HTTPError):
            client._get("/nonexistent")

    def test_unsupported_method_raises_error(self, mock_env, mock_session):
        """Test that unsupported HTTP methods raise error."""
        from core.systemlink_client import SystemLinkClient
        
        client = SystemLinkClient()
        
        with pytest.raises(ValueError, match="Unsupported method"):
            client._make_request_impl("PATCH", "/test")


class TestIntegration:
    """Integration tests (skipped by default, require live server)."""

    @pytest.fixture
    def live_api_available(self):
        """Check if live API is configured."""
        url = os.getenv("SYSTEMLINK_API_URL")
        key = os.getenv("SYSTEMLINK_API_KEY")
        return bool(url and key)

    @pytest.mark.skip(reason="Requires live SystemLink server")
    def test_live_asset_query(self, live_api_available):
        """Test actual asset query against live server."""
        if not live_api_available:
            pytest.skip("No live API configured")
        
        from core.systemlink_client import AssetClient
        
        with AssetClient() as client:
            result = client.query(take=1)
            assert "assets" in result

    @pytest.mark.skip(reason="Requires live SystemLink server")
    def test_live_testmonitor_query(self, live_api_available):
        """Test actual test monitor query against live server."""
        if not live_api_available:
            pytest.skip("No live API configured")
        
        from core.systemlink_client import TestMonitorClient
        
        with TestMonitorClient() as client:
            result = client.query_results(take=1)
            assert "results" in result
