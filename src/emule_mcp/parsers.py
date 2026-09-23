from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from .errors import InvalidLinkError, ParseError

_SESSION_RE = re.compile(r"ses=(\d+)")
_STATE_RE = re.compile(r"^(high|low|connecting|disconnected)\.gif$", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_HASH_RE = re.compile(r"^[0-9A-Fa-f]{32}$")
_ED2K_CALL_RE = re.compile(r"searchmenu\(event,'(.*)'\)")
_ED2K_FILE_RE = re.compile(r"ed2k://\|file\|([^|]*)\|(\d+)\|([0-9A-Fa-f]{32})\|/")
_SERVER_ROW_RE = re.compile(r"server-line-(high|low|connecting|disconnected|failed)-left")
_ED2K_SERVER_RE = re.compile(r"ed2k://\|server\|([^|]+)\|([^|]+)\|/")
_SERVER_PRIORITY_RE = re.compile(r"serverpriomenu\(event,(?:'[^']*',){4}'([^']*)'\)")
_DOWNLOAD_ROW_RE = re.compile(r"^down-line-([a-z]+)-left$")


@dataclass(frozen=True)
class Status:
    connection_state: str
    connection_text: str
    download: str
    upload: str
    kad: str


@dataclass(frozen=True)
class SearchResult:
    name: str
    size: str
    file_hash: str
    sources: str
    ed2k: str


@dataclass(frozen=True)
class SearchOutcome:
    message: str
    results: tuple[SearchResult, ...]


@dataclass(frozen=True)
class Server:
    name: str
    ip: str
    port: str
    state: str
    users: str
    files: str
    priority: str


@dataclass(frozen=True)
class Download:
    name: str
    size: str
    transferred: str
    speed: str
    sources: str
    priority: str
    category: str
    state: str
    file_hash: str
    ed2k: str


def extract_session(html: str) -> str | None:
    match = _SESSION_RE.search(html)
    return match.group(1) if match else None


def parse_status(html: str) -> Status:
    soup = BeautifulSoup(html, "html.parser")

    state_image = soup.find("img", src=_STATE_RE)
    if state_image is None:
        raise ParseError("cannot locate the connection state in the WebServer response")

    return Status(
        connection_state=_STATE_RE.match(state_image["src"]).group(1).lower(),
        connection_text=_cell_text(state_image),
        download=_value_after_label(_cell_text(_image(soup, "arrow_down.gif"))),
        upload=_value_after_label(_cell_text(_image(soup, "arrow_up.gif"))),
        kad=_cell_text(_image(soup, "h_kad.gif", align="left")),
    )


def parse_search(html: str) -> SearchOutcome:
    soup = BeautifulSoup(html, "html.parser")

    message_node = soup.find("font", attrs={"color": "#FFC412"})
    message = _normalize(message_node.get_text()).strip("()").strip() if message_node else ""

    results = []
    for checkbox in soup.find_all("input", attrs={"name": "downloads"}):
        file_hash = checkbox.get("value", "")
        if not _HASH_RE.match(file_hash):
            continue
        row = checkbox.find_parent("tr")
        if row is not None:
            results.append(_parse_search_result(row, file_hash))

    return SearchOutcome(message=message, results=tuple(results))


def parse_servers(html: str) -> tuple[Server, ...]:
    soup = BeautifulSoup(html, "html.parser")

    servers = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        state_match = _SERVER_ROW_RE.search(" ".join(cells[0].get("class", [])))
        if state_match is None:
            continue
        servers.append(_parse_server_row(cells, state_match.group(1)))

    return tuple(servers)


def parse_downloads(html: str) -> tuple[Download, ...]:
    soup = BeautifulSoup(html, "html.parser")

    downloads = []
    for cell in soup.find_all("td", class_=True):
        state = _download_state(cell)
        if state is None:
            continue
        row = cell.find_parent("tr")
        if row is not None:
            downloads.append(_parse_download_row(row, state))

    return tuple(downloads)


def extract_ed2k_hash(ed2k: str) -> str:
    match = _ED2K_FILE_RE.search(ed2k)
    if match is None:
        raise InvalidLinkError("expected an eD2k file link of the form ed2k://|file|...")
    return match.group(3)


def _parse_download_row(row: Tag, state: str) -> Download:
    cells = row.find_all("td", recursive=False)
    name_cell = cells[0].select_one("table tr td:last-child") if cells else None
    if name_cell is not None:
        for hidden in name_cell.find_all("div"):
            hidden.decompose()

    ed2k = _download_ed2k_link(row)
    match = _ED2K_FILE_RE.search(ed2k)

    return Download(
        name=_normalize(name_cell.get_text(" ", strip=True)) if name_cell else "",
        size=_normalize(_text(cells, 1)),
        transferred=_normalize(_text(cells, 2)),
        speed=_normalize(_text(cells, 4)),
        sources=_normalize(_text(cells, 5)),
        priority=_normalize(_text(cells, 6)),
        category=_normalize(_text(cells, 7)),
        state=state,
        file_hash=match.group(3) if match else "",
        ed2k=ed2k,
    )


def _download_state(cell: Tag) -> str | None:
    for css_class in cell.get("class", []):
        match = _DOWNLOAD_ROW_RE.match(css_class)
        if match:
            return match.group(1)
    return None


def _download_ed2k_link(row: Tag) -> str:
    for anchor in row.find_all("a"):
        match = _ED2K_FILE_RE.search(_attr(anchor, "onmouseover"))
        if match:
            return match.group(0)
    return ""


def _parse_search_result(row: Tag, file_hash: str) -> SearchResult:
    name_cell = row.select_one("td.search-line-left table tr td:last-child")
    size_cell = row.select_one("td.search-line-right")
    line_cells = row.select("td.search-line")
    sources_cell = line_cells[1] if len(line_cells) > 1 else None

    return SearchResult(
        name=name_cell.get_text(strip=True) if name_cell else "",
        size=size_cell.get_text(strip=True) if size_cell else "",
        file_hash=file_hash,
        sources=sources_cell.get_text(strip=True) if sources_cell else "",
        ed2k=_extract_ed2k(row),
    )


def _parse_server_row(cells: list[Tag], state: str) -> Server:
    first = cells[0]
    name_cell = first.select_one("table tr td:last-child")
    acronym = first.find("acronym")
    if acronym is not None and acronym.get("title"):
        name = acronym["title"].strip()
    else:
        name = name_cell.get_text(strip=True) if name_cell else ""

    ed2k_match = _ED2K_SERVER_RE.search(_attr(first.find("a"), "onmouseover"))
    ip, port = ed2k_match.groups() if ed2k_match else ("", "")

    priority_match = _SERVER_PRIORITY_RE.search(_attr(_cell_anchor(cells, 6), "onmouseover"))

    return Server(
        name=name,
        ip=ip,
        port=port,
        state=state,
        users=_text(cells, 4),
        files=_text(cells, 5),
        priority=priority_match.group(1) if priority_match else "",
    )


def _cell_anchor(cells: list[Tag], index: int) -> Tag | None:
    return cells[index].find("a") if index < len(cells) else None


def _text(cells: list[Tag], index: int) -> str:
    return cells[index].get_text(strip=True) if index < len(cells) else ""


def _attr(tag: Tag | None, name: str) -> str:
    if tag is None:
        return ""
    return next((value for key, value in tag.attrs.items() if key.lower() == name), "")


def _extract_ed2k(row: Tag) -> str:
    for anchor in row.find_all("a"):
        match = _ED2K_CALL_RE.search(_attr(anchor, "onmouseover"))
        if match:
            return match.group(1).replace("\\'", "'")
    return ""


def _image(soup: BeautifulSoup, src: str, align: str | None = None) -> Tag:
    image = soup.find("img", src=src, attrs={"align": align} if align else None)
    if image is None:
        raise ParseError(f"cannot locate the '{src}' image in the WebServer response")
    return image


def _cell_text(image: Tag) -> str:
    cell = image.find_parent("td")
    node = cell if cell is not None else image.parent
    return _normalize(node.get_text(" ", strip=True)) if node is not None else ""


def _value_after_label(text: str) -> str:
    _, separator, value = text.partition(":")
    return value.strip() if separator else text


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.replace("\xa0", " ")).strip()
