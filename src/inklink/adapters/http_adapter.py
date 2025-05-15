"""HTTP adapter for InkLink.

This module provides an adapter for making HTTP requests with consistent
error handling, retries, and configuration.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter as RequestsHTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class HTTPAdapter(Adapter):
    """Adapter for making HTTP requests with consistent error handling and retries."""

    def __init__(self, base_url: str = "", timeout: int = 10, retries: int = 3):
        """
        Initialize with base URL and request settings.

        Args:
            base_url: Base URL for requests
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
        """
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self.session = self._create_session()

    def ping(self) -> bool:
        """
        Check if the base URL is reachable.

        Returns:
            True if reachable, False otherwise
        """
        if not self.base_url:
            return False

        try:
            response = self.session.head(self.base_url, timeout=self.timeout)
            return response.status_code < 400
        except Exception:
            return False

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            # method_whitelist is deprecated in newer versions, use allowed_methods instead
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        )

        adapter = RequestsHTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(
            {
                "User-Agent": "InkLink/1.0",
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        return session

    def _get_url(self, endpoint: str) -> str:
        """
        Get full URL for the given endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Full URL
        """
        if endpoint.startswith(("http://", "https://")):
            return endpoint

        if self.base_url.endswith("/") and endpoint.startswith("/"):
            endpoint = endpoint[1:]

        return f"{self.base_url}{endpoint}"

    def get(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> Tuple[bool, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            Tuple of (success, response_or_error)
        """
        return self._request(
            "GET", endpoint, params=params, headers=headers, timeout=timeout
        )

    def post(
        self,
        endpoint: str,
        data: Any = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> Tuple[bool, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            data: Request data
            json: JSON data
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            Tuple of (success, response_or_error)
        """
        return self._request(
            "POST",
            endpoint,
            data=data,
            json=json,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def put(
        self,
        endpoint: str,
        data: Any = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> Tuple[bool, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint
            data: Request data
            json: JSON data
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            Tuple of (success, response_or_error)
        """
        return self._request(
            "PUT",
            endpoint,
            data=data,
            json=json,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def delete(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> Tuple[bool, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            Tuple of (success, response_or_error)
        """
        return self._request(
            "DELETE", endpoint, params=params, headers=headers, timeout=timeout
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Any = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> Tuple[bool, Any]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            json: JSON data
            params: Query parameters
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            Tuple of (success, response_or_error)
        """
        try:
            url = self._get_url(endpoint)
            timeout = timeout or self.timeout

            # Make request
            response = self.session.request(
                method,
                url,
                data=data,
                json=json,
                params=params,
                headers=headers,
                timeout=timeout,
            )

            # Check if successful
            response.raise_for_status()

            # Return response data
            try:
                return True, response.json()
            except ValueError:
                return True, response.text

        except requests.RequestException as e:
            # Log error
            logger.error(f"HTTP request failed: {str(e)}")

            # Return error response if available
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    return False, error_data
                except ValueError:
                    return False, e.response.text

            return False, str(e)

        except Exception as e:
            logger.error(f"Error making HTTP request: {str(e)}")
            return False, str(e)

    def download_file(
        self,
        url: str,
        local_path: str,
        headers: Dict[str, str] = None,
        timeout: int = None,
    ) -> bool:
        """
        Download a file from the given URL.

        Args:
            url: URL to download from
            local_path: Path to save file to
            headers: Request headers
            timeout: Request timeout (overrides default)

        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = timeout or self.timeout

            # Make request with stream=True to handle large files
            with self.session.get(
                url,
                headers=headers,
                timeout=timeout,
                stream=True,
            ) as response:
                response.raise_for_status()

                # Save file
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

            return True

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    def retry_request(
        self,
        request_fn: Callable,
        *args,
        max_retries: int = None,
        retry_delay: int = 1,
        **kwargs,
    ) -> Tuple[bool, Any]:
        """
        Retry a request function with exponential backoff.

        Args:
            request_fn: Request function to retry
            *args: Positional arguments for the request function
            max_retries: Maximum number of retries (overrides default)
            retry_delay: Initial delay between retries in seconds
            **kwargs: Keyword arguments for the request function

        Returns:
            Tuple of (success, response_or_error)
        """
        max_retries = max_retries or self.retries
        attempts = 0
        last_error = None

        while attempts <= max_retries:
            try:
                if attempts > 0:
                    logger.info(f"Retry attempt {attempts}")

                return request_fn(*args, **kwargs)

            except Exception as e:
                last_error = e
                attempts += 1

                if attempts <= max_retries:
                    sleep_time = retry_delay * (2 ** (attempts - 1))
                    logger.warning(
                        f"Request failed, retrying in {sleep_time} seconds: {str(e)}"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(
                        f"Request failed after {max_retries} retries: {str(e)}"
                    )

        return False, str(last_error)
