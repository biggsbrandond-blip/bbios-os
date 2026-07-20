from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from bbi_os.core.error_system.exceptions import BBIOSError
from bbi_os.observability import current_request_id, timestamp


def _request_id() -> Optional[str]:
    request_id = current_request_id()
    if request_id == "system":
        return None
    return request_id


def _error_payload(exception: Exception) -> Dict[str, Any]:
    return {
        "error": True,
        "type": exception.__class__.__name__,
        "message": str(exception),
        "request_id": _request_id(),
        "timestamp": timestamp(),
    }


async def bbios_exception_handler(
    request: Request, exception: BBIOSError
) -> JSONResponse:
    return JSONResponse(status_code=500, content=_error_payload(exception))


async def generic_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    return JSONResponse(status_code=500, content=_error_payload(exception))
