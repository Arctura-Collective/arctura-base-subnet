"""Environment generator security tests."""

from scripts import generate_env


def test_check_rpc_rejects_non_http_schemes(monkeypatch):
    monkeypatch.setattr(
        generate_env.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not request")),
    )

    reachable, message = generate_env.check_rpc("file:///etc/passwd")

    assert reachable is False
    assert "http:// or https://" in message


def test_check_rpc_accepts_json_rpc_block_response(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": "0x10"}

    monkeypatch.setattr(generate_env.httpx, "post", lambda *args, **kwargs: Response())

    assert generate_env.check_rpc("https://base.example") == (True, "block #16")
