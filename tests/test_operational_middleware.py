import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from uuid import UUID

from bbi_os import api
from bbi_os.app import create_app
from bbi_os.observability import (
    REQUEST_ID_HEADER,
    Observability,
    normalize_request_id,
    set_observability,
)
from bbi_os.settings import reset_settings_cache


Headers = Iterable[Tuple[bytes, bytes]]


async def call_asgi(
    application,
    method: str,
    path: str,
    headers: Headers = (),
    body: bytes = b"",
) -> Dict[str, object]:
    messages: List[Dict[str, object]] = []
    sent = False

    async def receive() -> Dict[str, object]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: Dict[str, object]) -> None:
        messages.append(message)

    await application(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": list(headers),
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    start = next(message for message in messages if message["type"] == "http.response.start")
    body_parts = [
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ]
    return {
        "status": start["status"],
        "headers": {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in start["headers"]
        },
        "body": b"".join(body_parts),
    }


class OperationalMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        os.environ["BBIOS_DATA_DIR"] = str(self.root)
        reset_settings_cache()
        api.v1._client_handler.cache_clear()
        api.v1._task_service.cache_clear()
        self.stream = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.stream.close()
        self.temporary_directory.cleanup()
        os.environ.pop("BBIOS_DATA_DIR", None)
        reset_settings_cache()
        api.v1._client_handler.cache_clear()
        api.v1._task_service.cache_clear()

    def records(self) -> List[Dict[str, object]]:
        self.stream.seek(0)
        return [json.loads(line) for line in self.stream if line.strip()]

    def test_health_response_is_unchanged_and_echoes_inbound_request_id(self) -> None:
        response = asyncio.run(
            call_asgi(
                create_app(),
                "GET",
                "/health",
                [(REQUEST_ID_HEADER.lower().encode("ascii"), b"phase3-request-1")],
            )
        )

        self.assertEqual(200, response["status"])
        self.assertEqual({"status": "ok"}, json.loads(response["body"]))
        self.assertEqual("phase3-request-1", response["headers"][REQUEST_ID_HEADER.lower()])
        self.assertTrue(
            any(
                record["event"] == "fastapi_request_completed"
                and record["request_id"] == "phase3-request-1"
                for record in self.records()
            )
        )

    def test_missing_request_id_generates_response_header(self) -> None:
        response = asyncio.run(call_asgi(create_app(), "GET", "/health"))

        request_id = response["headers"][REQUEST_ID_HEADER.lower()]
        UUID(request_id)
        self.assertEqual({"status": "ok"}, json.loads(response["body"]))

    def test_invalid_request_id_is_not_reused(self) -> None:
        self.assertNotEqual("bad id", normalize_request_id("bad id"))

        response = asyncio.run(
            call_asgi(
                create_app(),
                "GET",
                "/health",
                [(REQUEST_ID_HEADER.lower().encode("ascii"), b"bad id")],
            )
        )

        request_id = response["headers"][REQUEST_ID_HEADER.lower()]
        self.assertNotEqual("bad id", request_id)
        UUID(request_id)

    def test_handler_response_body_request_id_uses_inbound_request_id(self) -> None:
        payload = json.dumps({"name": "Operational Client", "plan": "Pro"}).encode(
            "utf-8"
        )
        response = asyncio.run(
            call_asgi(
                create_app(),
                "POST",
                "/clients",
                [
                    (REQUEST_ID_HEADER.lower().encode("ascii"), b"client-request-1"),
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                ],
                payload,
            )
        )
        body = json.loads(response["body"])

        self.assertEqual(201, response["status"])
        self.assertEqual("client-request-1", response["headers"][REQUEST_ID_HEADER.lower()])
        self.assertEqual("client-request-1", body["request_id"])
        self.assertEqual("success", body["status"])
        self.assertEqual("Operational Client", body["data"]["name"])


if __name__ == "__main__":
    unittest.main()
