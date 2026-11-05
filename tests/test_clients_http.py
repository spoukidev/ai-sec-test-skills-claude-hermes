"""Exercise the *real* Anthropic and OpenAI SDK clients against a local stub HTTP server.

No external network and no real keys: the server runs on 127.0.0.1 and returns canned responses in
each provider's wire format. This checks request shaping and response parsing end to end.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from aisec.config import TargetConfig
from aisec.models.base import build_client
from aisec.schema import Message
from aisec.tool_catalog import get_tools

SEEN: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append(
            {"path": self.path, "body": body, "headers": {k.lower(): v for k, v in self.headers.items()}}
        )
        if self.path.endswith("/messages"):
            out = {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "content": [
                    {"type": "text", "text": "I can't share that."},
                    {"type": "tool_use", "id": "tu_1", "name": "search_docs", "input": {"query": "x"}},
                ],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            }
        else:
            out = {
                "id": "cmpl_1",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": "Sure.",
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {
                                        "name": "http_get",
                                        "arguments": '{"url": "https://a.example"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 2, "total_tokens": 11},
            }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_anthropic_sdk_roundtrip(server, monkeypatch):
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "test-not-a-key")
    t = TargetConfig(
        name="claude",
        provider="anthropic",
        model="claude-test",
        api_key_env=["TEST_ANTHROPIC_KEY"],
        base_url=server,
    )
    c = build_client(t)
    r = c.complete("SYS", [Message(role="user", content="hi")], get_tools(["search_docs"]))
    req = SEEN[-1]
    assert req["path"].endswith("/v1/messages")
    assert req["body"]["system"] == "SYS" and req["body"]["tools"][0]["name"] == "search_docs"
    # the key from the env var reaches the wire (header name depends on the SDK version)
    h = req["headers"]
    assert h.get("x-api-key") == "test-not-a-key" or h.get("authorization") == "Bearer test-not-a-key"
    assert r.text == "I can't share that." and r.tool_calls[0].arguments == {"query": "x"}
    assert r.usage.input_tokens == 12 and r.model_id == "claude-test"


def test_openai_compat_sdk_roundtrip(server, monkeypatch):
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-not-a-key")
    t = TargetConfig(
        name="hermes",
        provider="openai_compat",
        model="hermes-test",
        api_key_env=["TEST_OPENAI_KEY"],
        base_url=server + "/v1",
        params={"temperature": 0},
    )
    c = build_client(t)
    r = c.complete("SYS", [Message(role="user", content="hi")], get_tools(["http_get"]))
    req = SEEN[-1]
    assert req["path"] == "/v1/chat/completions"
    assert req["body"]["messages"][0] == {"role": "system", "content": "SYS"}
    assert req["body"]["temperature"] == 0 and req["body"]["tools"][0]["type"] == "function"
    assert req["headers"].get("authorization") == "Bearer test-not-a-key"
    assert r.text == "Sure." and r.tool_calls[0].name == "http_get"
    assert r.usage.output_tokens == 2 and r.model_id == "hermes-test"
