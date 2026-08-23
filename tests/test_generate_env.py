"""Environment generator security tests."""

from scripts import generate_env


def test_check_rpc_rejects_non_http_schemes(monkeypatch):
    monkeypatch.setattr(
        generate_env.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not request")),
    )

    reachable, message = generate_env.check_rpc("file:///etc/passwd")

    assert reachable is False
    assert "http:// or https://" in message


def test_check_rpc_accepts_json_rpc_block_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"result": "0x10"}'

    monkeypatch.setattr(generate_env.urllib.request, "urlopen", lambda *args, **kwargs: Response())

    assert generate_env.check_rpc("https://base.example") == (True, "block #16")
