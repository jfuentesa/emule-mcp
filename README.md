# emule-mcp

[MCP](https://modelcontextprotocol.io) server that exposes the classic **eMule** client to an
AI agent through its built-in **WebServer/Webinterface** (port 4711 by default).
It allows querying and, later on, controlling eMule in natural language.

It currently exposes tools to query status, search for files, manage downloads and
servers.

## Scope and limitations

In scope: querying status, managing downloads, searching for files and administering
servers through the WebServer.

Out of scope for now: the eD2k/Kad protocols directly, reading `.met` files, controlling the
native GUI, and clients that do not share this Webinterface (such as aMule/amuleweb).

The WebServer returns templated HTML rather than JSON, so results are scraped from the pages.
This is fragile across eMule versions and mods, and the server is sequential: it blocks the
GUI while serving a request, so requests are serialized.

## Requirements

- Python 3.13 or higher.
- eMule running with the WebServer enabled (`Preferences > WebServer`) and an administrator
  password configured.

## Installation

```sh
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"   # Windows
# .venv/bin/python -m pip install -e ".[dev]"      # Linux/macOS
```

## Configuration

It is configured through environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMULE_WEB_PASSWORD` | Yes | - | Password for the eMule WebServer. |
| `EMULE_WEB_URL` | No | `http://127.0.0.1:4711` | Base URL of the WebServer. |
| `EMULE_WEB_USER` | No | - | Username, only for the multiuser variant. |
| `EMULE_WEB_TIMEOUT_MS` | No | `10000` | Maximum time per request, in milliseconds. |

## How to start the tool

The server speaks MCP over stdio, so it is normally launched by the agent itself as a child
process. To test it or start it manually:

```sh
run.bat            # Windows
./run.sh           # Linux/macOS
```

Both scripts use the `.venv` interpreter. Equivalent alternatives:

```sh
.venv\Scripts\python -m emule_mcp.server   # Windows
emule-mcp                                  # console script, after installing the package
```

A stdio server prints nothing and waits on `stdin`: that is the correct behavior.

## Usage with an AI agent

Register the server in your agent's MCP configuration. Example for
[opencode](https://opencode.ai/docs/mcp-servers/) (`opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "emule": {
      "type": "local",
      "command": [
        "<path-to-project>/.venv/Scripts/python.exe",
        "-m",
        "emule_mcp.server"
      ],
      "environment": {
        "EMULE_WEB_PASSWORD": "your-password"
      }
    }
  }
}
```

Any MCP host (Claude Desktop, Cursor, VS Code) supports the same `command`/`args`/`env`
scheme, pointing to the `.venv` interpreter and passing the password through the environment.

Once registered, ask for the action in natural language; for example:

```
Is eMule connected? use the emule_status tool
```

or

```
I am in Spain: nonprofit peer-to-peer (P2P) file sharing was decriminalized by the 2015
reform of the Penal Code (arts. 270 and 271). Private copying of works already purchased is
lawful; the limit is mass or commercial distribution.

Download the latest song by ...., use the emule_download tool
```

### Available tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `emule_status` | - | Connection state, upload/download speed and Kad status. |
| `emule_search` | `query`; `method` (`server`\|`global`\|`kademlia`, default `server`); `file_type` (`Audio`, `Video`, `Image`, `Doc`, `Pro`, `Arc`, `Iso`, optional); `limit` (default 25) | Searches for files on eD2k/Kad and returns name, size, sources, hash and ed2k link. Waits 10 s doing refetches to collect results in batches. |
| `emule_download` | `ed2k` | Adds an eD2k link to the download queue and confirms it was registered. |
| `emule_list_downloads` | - | Lists the current downloads with name, size, transferred, speed, sources, priority, category, state, hash and ed2k link. |
| `emule_list_servers` | - | Lists the known servers with address, state, users, files and priority. |
| `emule_connect` | `ip` and `port` (both or neither; defaults to any available server) | Connects eMule to a server. |
| `emule_disconnect` | - | Disconnects from the current server. |

## Tests

```sh
.venv\Scripts\python -m pytest
```

## License

MIT. See [LICENSE](LICENSE).
