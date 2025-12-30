"""
비동기 HTTP 클라이언트
외부 API 호출을 위한 통합 클라이언트
"""
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.constants import HTTPHeaders, Timeouts
from app.core.exceptions import ExternalServiceError, JavaAPIError

logger = logging.getLogger(__name__)


class AsyncHttpClient:
    """
    비동기 HTTP 클라이언트
    httpx 기반으로 비동기 HTTP 요청 처리
    """

    def __init__(
        self,
        timeout: float = Timeouts.JAVA_API,
        verify_ssl: bool = False,
        base_url: Optional[str] = None
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """클라이언트 인스턴스 반환 (lazy initialization)"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                verify=self.verify_ssl,
                base_url=self.base_url or ""
            )
        return self._client

    async def close(self):
        """클라이언트 연결 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        GET 요청

        Args:
            url: 요청 URL
            headers: HTTP 헤더
            params: 쿼리 파라미터

        Returns:
            JSON 응답
        """
        client = await self._get_client()
        try:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {url}")
            raise ExternalServiceError(
                service="HTTP",
                message=f"HTTP {e.response.status_code}",
                original_error=e
            )
        except httpx.RequestError as e:
            logger.error(f"요청 오류: {e}")
            raise ExternalServiceError(
                service="HTTP",
                message="요청 실패",
                original_error=e
            )

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        POST 요청

        Args:
            url: 요청 URL
            json: JSON 바디
            headers: HTTP 헤더
            data: Form 데이터

        Returns:
            JSON 응답
        """
        client = await self._get_client()
        try:
            response = await client.post(
                url,
                json=json,
                headers=headers,
                data=data,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {url}")
            raise ExternalServiceError(
                service="HTTP",
                message=f"HTTP {e.response.status_code}",
                original_error=e
            )
        except httpx.RequestError as e:
            logger.error(f"요청 오류: {e}")
            raise ExternalServiceError(
                service="HTTP",
                message="요청 실패",
                original_error=e
            )


class JavaAPIClient:
    """
    Java API 전용 클라이언트
    Basic Auth 및 공통 헤더 처리
    """

    def __init__(
        self,
        base_url: str,
        basic_auth: str,
        timeout: float = Timeouts.JAVA_API
    ):
        self.base_url = base_url.rstrip("/")
        self.basic_auth = basic_auth
        self.timeout = timeout
        self._client = AsyncHttpClient(
            timeout=timeout,
            verify_ssl=False
        )

    def _get_headers(self) -> Dict[str, str]:
        """공통 헤더 반환"""
        return {
            HTTPHeaders.AUTHORIZATION: self.basic_auth,
            HTTPHeaders.CONTENT_TYPE: HTTPHeaders.JSON_CONTENT
        }

    async def post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Java API POST 요청

        Args:
            endpoint: API 엔드포인트 (예: "/questions/add")
            payload: 요청 바디
            extra_headers: 추가 헤더

        Returns:
            JSON 응답

        Raises:
            JavaAPIError: Java API 호출 실패
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            logger.debug(f"Java API 요청: {endpoint}")
            response = await self._client.post(url, json=payload, headers=headers)
            return response
        except ExternalServiceError as e:
            raise JavaAPIError(
                endpoint=endpoint,
                message=str(e),
                original_error=e
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Java API GET 요청

        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            extra_headers: 추가 헤더

        Returns:
            JSON 응답
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            logger.debug(f"Java API GET 요청: {endpoint}")
            response = await self._client.get(url, headers=headers, params=params)
            return response
        except ExternalServiceError as e:
            raise JavaAPIError(
                endpoint=endpoint,
                message=str(e),
                original_error=e
            )

    async def close(self):
        """클라이언트 종료"""
        await self._client.close()


# ===========================================
# 동기 클라이언트 (기존 코드 호환용)
# ===========================================

class SyncHttpClient:
    """
    동기 HTTP 클라이언트
    기존 requests 기반 코드와의 호환성을 위해 제공
    점진적으로 AsyncHttpClient로 마이그레이션 권장
    """

    def __init__(
        self,
        timeout: float = Timeouts.JAVA_API,
        verify_ssl: bool = False
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """동기 POST 요청"""
        import requests

        try:
            response = requests.post(
                url,
                json=json,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {url}")
            raise ExternalServiceError(
                service="HTTP",
                message=f"HTTP {e.response.status_code}",
                original_error=e
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"요청 오류: {e}")
            raise ExternalServiceError(
                service="HTTP",
                message="요청 실패",
                original_error=e
            )

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """동기 GET 요청"""
        import requests

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {url}")
            raise ExternalServiceError(
                service="HTTP",
                message=f"HTTP {e.response.status_code}",
                original_error=e
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"요청 오류: {e}")
            raise ExternalServiceError(
                service="HTTP",
                message="요청 실패",
                original_error=e
            )


class SyncJavaAPIClient:
    """
    동기 Java API 클라이언트
    기존 코드와의 호환성을 위해 제공
    """

    def __init__(
        self,
        base_url: str,
        basic_auth: str,
        timeout: float = Timeouts.JAVA_API
    ):
        self.base_url = base_url.rstrip("/")
        self.basic_auth = basic_auth
        self._client = SyncHttpClient(timeout=timeout, verify_ssl=False)

    def _get_headers(self) -> Dict[str, str]:
        return {
            HTTPHeaders.AUTHORIZATION: self.basic_auth,
            HTTPHeaders.CONTENT_TYPE: HTTPHeaders.JSON_CONTENT
        }

    def post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """동기 POST 요청"""
        url = f"{self.base_url}{endpoint}"
        try:
            return self._client.post(url, json=payload, headers=self._get_headers())
        except ExternalServiceError as e:
            raise JavaAPIError(endpoint=endpoint, message=str(e), original_error=e)
