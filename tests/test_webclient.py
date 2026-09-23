import pytest

from emule_mcp.config import Config
from emule_mcp.errors import AuthenticationError, EMuleOfflineError
from emule_mcp.webclient import EMuleWebClient

LOGIN_PAGE = "<html><body>please log in</body></html>"
HEADER_WITH_SESSION = '<html><body><a href="?ses=777&w=transfer">transfer</a></body></html>'


class _Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class _StubHttp:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        return self._responses.pop(0)

    def close(self):
        pass


def _config():
    return Config(base_url="http://127.0.0.1:4711", password="secret")


def test_login_sends_plain_password_and_uses_session():
    http = _StubHttp([_Response(HEADER_WITH_SESSION), _Response(HEADER_WITH_SESSION)])
    client = EMuleWebClient(_config(), http_client=http)

    client.fetch_page("transfer")

    assert http.calls[0] == ("/", {"w": "password", "p": "secret"})
    assert http.calls[1] == ("/", {"ses": "777", "w": "transfer"})


def test_relogins_when_session_expires():
    http = _StubHttp(
        [
            _Response(HEADER_WITH_SESSION),
            _Response(LOGIN_PAGE),
            _Response(HEADER_WITH_SESSION),
            _Response(HEADER_WITH_SESSION),
        ]
    )
    client = EMuleWebClient(_config(), http_client=http)

    client.fetch_page("transfer")

    assert [call[1]["w"] for call in http.calls] == [
        "password",
        "transfer",
        "password",
        "transfer",
    ]


def test_wrong_password_raises_authentication_error():
    http = _StubHttp([_Response(LOGIN_PAGE)])
    client = EMuleWebClient(_config(), http_client=http)

    with pytest.raises(AuthenticationError):
        client.fetch_page("transfer")


def test_non_ok_status_raises_offline_error():
    http = _StubHttp([_Response("nope", status_code=500)])
    client = EMuleWebClient(_config(), http_client=http)

    with pytest.raises(EMuleOfflineError):
        client.fetch_page("transfer")
