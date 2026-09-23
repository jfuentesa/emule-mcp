from __future__ import annotations

from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .config import Config
from .errors import EMuleMCPError
from .parsers import Download, Status
from .service import EMuleService
from .webclient import EMuleWebClient

mcp = MCPServer("eMule")

_client: EMuleWebClient | None = None


def _service() -> EMuleService:
    global _client
    if _client is None:
        _client = EMuleWebClient(Config.from_env())
    return EMuleService(_client)


def _status_fields(status: Status) -> dict[str, str]:
    return {
        "connection_state": status.connection_state,
        "connection_text": status.connection_text,
        "download": status.download,
        "upload": status.upload,
        "kad": status.kad,
    }


def _download_fields(download: Download) -> dict[str, str]:
    return {
        "name": download.name,
        "size": download.size,
        "transferred": download.transferred,
        "speed": download.speed,
        "sources": download.sources,
        "priority": download.priority,
        "category": download.category,
        "state": download.state,
        "hash": download.file_hash,
        "ed2k": download.ed2k,
    }


@mcp.tool()
def emule_status() -> dict[str, str]:
    """Return the connection state, transfer rates and Kad status of eMule."""
    try:
        status = _service().get_status()
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    return _status_fields(status)


@mcp.tool()
def emule_list_servers() -> dict:
    """List the servers known to eMule with their address, state, users and priority."""
    try:
        servers = _service().list_servers()
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    return {
        "count": len(servers),
        "servers": [
            {
                "name": server.name,
                "ip": server.ip,
                "port": server.port,
                "state": server.state,
                "users": server.users,
                "files": server.files,
                "priority": server.priority,
            }
            for server in servers
        ],
    }


@mcp.tool()
def emule_connect(ip: str | None = None, port: int | None = None) -> dict[str, str]:
    """Connect eMule to a server. With no arguments, connect to any available server."""
    if (ip is None) != (port is None):
        raise ToolError("provide both ip and port, or neither")

    try:
        status = _service().connect(ip=ip, port=port)
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    return _status_fields(status)


@mcp.tool()
def emule_disconnect() -> dict[str, str]:
    """Disconnect eMule from its current server."""
    try:
        status = _service().disconnect()
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    return _status_fields(status)


@mcp.tool()
def emule_download(ed2k: str) -> dict:
    """Add an eD2k file link to eMule's download queue and confirm it was queued."""
    try:
        download = _service().add_download(ed2k)
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    if download is None:
        return {"message": "link sent to eMule but not found in the download list yet"}

    return {"message": "download queued", "download": _download_fields(download)}


@mcp.tool()
def emule_list_downloads() -> dict:
    """List the files currently in eMule's download queue."""
    try:
        downloads = _service().list_downloads()
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    return {
        "count": len(downloads),
        "downloads": [_download_fields(download) for download in downloads],
    }


@mcp.tool()
def emule_search(
    query: str,
    method: Literal["server", "global", "kademlia"] = "server",
    file_type: Literal["Audio", "Video", "Image", "Doc", "Pro", "Arc", "Iso"] | None = None,
    limit: int = 25,
) -> dict:
    """Search for files on eD2k or Kad, returning name, size, sources and ed2k link."""
    if limit < 1:
        raise ToolError("limit must be >= 1")

    try:
        outcome = _service().search(query, method=method, file_type=file_type)
    except EMuleMCPError as exc:
        raise ToolError(str(exc)) from exc

    results = [
        {
            "name": result.name,
            "size": result.size,
            "sources": result.sources,
            "hash": result.file_hash,
            "ed2k": result.ed2k,
        }
        for result in outcome.results[:limit]
    ]
    return {"message": outcome.message, "count": len(results), "results": results}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
