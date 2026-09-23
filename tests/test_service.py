import pytest

import emule_mcp.service as service_module
from emule_mcp.errors import InvalidLinkError
from emule_mcp.service import EMuleService


def _page(*hashes):
    rows = "".join(
        "<tr>"
        '<td class="search-line-left"><table class="search-line"><tr>'
        "<td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>"
        f"<td>f{h}.mp3</td>"
        "</tr></table></td>"
        '<td class="search-line-right">1 MB</td>'
        f'<td class="search-line">{h}</td>'
        '<td class="search-line">1(1)</td>'
        f'<td class="search-line"><input type="checkbox" name="downloads" value="{h}"></td>'
        "</tr>"
        for h in hashes
    )
    return f'<html><body><font color="#FFC412">(Search in progress)</font>{rows}</body></html>'


class _FakeClient:
    def __init__(self, pages):
        self._pages = list(pages)
        self.requested = []

    def fetch_page(self, page, **params):
        self.requested.append((page, params))
        return self._pages.pop(0)


STATUS_PAGE = (
    "<html><body>"
    '<td><img src="high.gif" align="left">Server</td>'
    '<td><img src="h_kad.gif" align="left">Kad ok</td>'
    '<td><img src="arrow_down.gif" align="left"> Down: 1.0 (2.0)</td>'
    '<td><img src="arrow_up.gif" align="left"> Up: 3.0 (4.0)</td>'
    "</body></html>"
)


def test_search_collects_results_across_refetches(monkeypatch):
    first, second = "A" * 32, "B" * 32
    client = _FakeClient([_page(first), _page(first, second)])
    sleeps = []
    monkeypatch.setattr(service_module.time, "sleep", sleeps.append)

    outcome = EMuleService(client).search("marc", wait_seconds=2, poll_seconds=2)

    assert [result.file_hash for result in outcome.results] == [first, second]
    assert sleeps == [2]
    assert client.requested[0] == ("search", {"tosearch": "marc", "method": "server"})
    assert client.requested[1] == ("search", {})


def test_search_without_wait_does_not_sleep(monkeypatch):
    def fail(_):
        raise AssertionError("search must not sleep when wait_seconds is 0")

    client = _FakeClient([_page("A" * 32)])
    monkeypatch.setattr(service_module.time, "sleep", fail)

    outcome = EMuleService(client).search("marc", wait_seconds=0)

    assert len(outcome.results) == 1
    assert len(client.requested) == 1


def test_connect_with_address_reports_status():
    client = _FakeClient(["<html></html>", STATUS_PAGE])

    status = EMuleService(client).connect(ip="1.2.3.4", port=4661)

    assert client.requested[0] == ("server", {"c": "connect", "ip": "1.2.3.4", "port": "4661"})
    assert client.requested[1] == ("transfer", {})
    assert status.connection_state == "high"


def test_connect_without_address_connects_to_any():
    client = _FakeClient(["<html></html>", STATUS_PAGE])

    EMuleService(client).connect()

    assert client.requested[0] == ("server", {"c": "connect"})


def test_disconnect():
    client = _FakeClient(["<html></html>", STATUS_PAGE])

    EMuleService(client).disconnect()

    assert client.requested[0] == ("server", {"c": "disconnect"})


def _downloads_page(*hashes):
    rows = "".join(
        "<tr>"
        '<td class="down-line-downloading-left">'
        '<table class="down-line-downloading-left"><tr>'
        "<td><a onMouseover=\"downmenu(event,'admin','info','ed2k://|file|"
        f"f{h}.mp3|4500000|{h}|/','downloading','disabled','f{h}.mp3','42','{h}','','yes')\">"
        '<img src="t_downloading.gif"></a></td>'
        f"<td>f{h}.mp3</td>"
        "</tr></table></td>"
        '<td class="down-line-downloading-right">4.29 MB</td>'
        '<td class="down-line-downloading-right">1.00 MB</td>'
        '<td class="down-line-downloading">bar</td>'
        '<td class="down-line-downloading-right">12.30</td>'
        '<td class="down-line-downloading">1 / 2 (1)</td>'
        '<td class="down-line-downloading">Normal</td>'
        '<td class="down-line-downloading">Default</td>'
        '<td class="down-line-downloading">checked_no</td>'
        "</tr>"
        for h in hashes
    )
    return f"<html><body><table>{rows}</table></body></html>"


def test_list_downloads():
    file_hash = "A" * 32
    client = _FakeClient([_downloads_page(file_hash)])

    downloads = EMuleService(client).list_downloads()

    assert client.requested == [("transfer", {})]
    assert downloads[0].file_hash == file_hash
    assert downloads[0].name == f"f{file_hash}.mp3"


def test_add_download_confirms_the_queued_file():
    file_hash = "C" * 32
    link = f"ed2k://|file|Los Van Van - Somos.mp3|4500000|{file_hash}|/"
    client = _FakeClient([_downloads_page(file_hash)])

    download = EMuleService(client).add_download(link)

    assert client.requested == [
        ("transfer", {"ed2k": f"ed2k://|file|Los%20Van%20Van%20-%20Somos.mp3|4500000|{file_hash}|/"})
    ]
    assert download is not None
    assert download.file_hash == file_hash


def test_add_download_keeps_existing_percent_encoding():
    file_hash = "D" * 32
    link = f"ed2k://|file|A%20B.mp3|4500000|{file_hash}|/"
    client = _FakeClient([_downloads_page(file_hash)])

    EMuleService(client).add_download(link)

    assert client.requested[0][1]["ed2k"] == link


def test_add_download_returns_none_when_not_listed():
    link = f"ed2k://|file|x.mp3|4500000|{'B' * 32}|/"
    client = _FakeClient([_downloads_page("A" * 32)])

    assert EMuleService(client).add_download(link) is None


def test_add_download_rejects_invalid_link_before_any_request():
    client = _FakeClient([])

    with pytest.raises(InvalidLinkError):
        EMuleService(client).add_download("not a link")

    assert client.requested == []
