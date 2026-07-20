from fastapi import FastAPI

from bbi_os.core.error_system.exceptions import BBIOSError
from bbi_os.core.error_system.handlers import (
    bbios_exception_handler,
    generic_exception_handler,
)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BBIOSError, bbios_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
