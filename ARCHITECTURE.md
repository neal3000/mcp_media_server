# MCP Media Server - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Media Server                            │
│                       (media_server.py)                             │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Core Components                          │   │
│  │                                                             │   │
│  │  • Server Instance (mcp.server.Server)                     │   │
│  │  • Tool Handlers (@app.list_tools, @app.call_tool)        │   │
│  │  • Media File Scanner (get_media_files)                    │   │
│  │  • Media Player Controller (play_media_file)               │   │
│  │                                                             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   stdio      │  │   HTTP/SSE   │  │  HTTPS/SSE   │            │
│  │  Transport   │  │  Transport   │  │  Transport   │            │
│  │              │  │              │  │              │            │
│  │ stdin/stdout │  │ Starlette    │  │ Starlette    │            │
│  │              │  │ + Uvicorn    │  │ + Uvicorn    │            │
│  │              │  │              │  │ + SSL        │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
└─────────┼──────────────────┼──────────────────┼───────────────────┘
          │                  │                  │
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼───────────────────┐
│         │                  │                  │                   │
│  ┌──────▼───────┐  ┌───────▼──────┐  ┌───────▼──────┐           │
│  │   stdio      │  │   HTTP/SSE   │  │  HTTPS/SSE   │           │
│  │   Client     │  │   Client     │  │   Client     │           │
│  │              │  │              │  │              │           │
│  │ subprocess   │  │  httpx       │  │  httpx       │           │
│  │ pipe         │  │  + SSE       │  │  + SSE       │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
│                    MCP Media Client                               │
│                   (media_client.py)                               │
└───────────────────────────────────────────────────────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  User Interface  │
                    │                  │
                    │  • Command Line  │
                    │  • Claude Desktop│
                    │  • n8n Workflow  │
                    │  • Custom Apps   │
                    └──────────────────┘
```

## Data Flow

### 1. List Movies Flow

```
User Command
    │
    ├─→ media_client.py --protocol stdio --command list
    │
    └─→ MCP Client Session
            │
            ├─→ Initialize Connection (stdio/http/https)
            │
            └─→ Call Tool: list_movies
                    │
                    └─→ media_server.py
                            │
                            ├─→ Scan ~/Media/MOVIES
                            │
                            ├─→ Filter by extensions (.mp4, .mkv, etc.)
                            │
                            ├─→ Get file stats (name, size, type)
                            │
                            └─→ Return formatted list
                                    │
                                    └─→ Display to user
```

### 2. Play Movie Flow

```
User Command
    │
    ├─→ media_client.py --protocol http --command play --movie "Airplane!.mp4"
    │
    └─→ MCP Client Session
            │
            ├─→ Connect to HTTP server
            │
            └─→ Call Tool: play_movie {"filename": "Airplane!.mp4"}
                    │
                    └─→ media_server.py
                            │
                            ├─→ Validate file exists
                            │
                            ├─→ Check file extension
                            │
                            ├─→ Detect platform (Linux/macOS/Windows)
                            │
                            ├─→ Find available player (VLC/MPV/etc.)
                            │
                            └─→ Launch player with subprocess.Popen
                                    │
                                    └─→ Return status message
                                            │
                                            └─→ Display to user
```

## Components

### media_server.py (9.6KB)

**Purpose:** MCP server that exposes media control tools

**Key Functions:**
- `get_media_files()` - Scans and returns media file list
- `play_media_file(filename)` - Launches media player
- `@app.list_tools()` - Registers available tools
- `@app.call_tool()` - Handles tool invocations
- `run_stdio()` - stdio transport handler
- `create_sse_app()` - HTTP/HTTPS transport setup
- `run_http_server()` - HTTP/HTTPS server launcher

**Transports:**
1. **stdio** - Process-based communication (stdin/stdout)
2. **HTTP** - Server-Sent Events (SSE) over HTTP
3. **HTTPS** - SSE over TLS/SSL

### media_client.py (4.5KB)

**Purpose:** Universal client for testing all transports

**Key Functions:**
- `connect_stdio()` - Establishes stdio connection
- `connect_http()` - Establishes HTTP/HTTPS connection
- `list_movies()` - Invokes list_movies tool
- `play_movie()` - Invokes play_movie tool

**Arguments:**
- `--protocol` - Transport selection (stdio/http/https)
- `--command` - Action (list/play)
- `--movie` - Filename for play command
- `--url` - Server URL for HTTP/HTTPS
- `--server-script` - Path to server for stdio

## Integration Points

### 1. Claude Desktop

**Configuration:** `claude_desktop_config.json`
```json
{
  "mcpServers": {
    "media-server": {
      "command": "python",
      "args": ["/path/to/media_server.py", "--transport", "stdio"]
    }
  }
}
```

**Usage:** Natural language commands
- "What movies are available?"
- "Play Airplane!.mp4"
- "List all movies in my collection"

### 2. n8n Workflow

**Nodes:**
1. HTTP Request → GET /sse (establish connection)
2. HTTP Request → POST /messages (send commands)

**Use Cases:**
- Scheduled playback
- Event-triggered movie selection
- Integration with other automation

### 3. Custom Applications

**Direct MCP Client:**
```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client

# Connect and use the server
async with stdio_client(...) as streams:
    session = ClientSession(streams[0], streams[1])
    await session.initialize()
    result = await session.call_tool("list_movies", {})
```

**HTTP API:**
```bash
# Use standard HTTP requests
curl -X POST http://localhost:8000/messages \
    -H "Content-Type: application/json" \
    -d '{"method": "tools/call", "params": {...}}'
```

## Security Considerations

1. **stdio:** Inherits permissions of parent process
2. **HTTP:** No authentication (use firewall rules)
3. **HTTPS:** Encrypted transport (use proper certificates)

**Recommendations:**
- Use stdio for local/trusted environments
- Use HTTPS for remote access
- Restrict --host to specific IPs in production
- Consider adding authentication for HTTP/HTTPS

## Performance

- **Startup Time:** < 1 second
- **List Operation:** O(n) where n = number of files
- **Play Operation:** O(1) - async subprocess launch
- **Memory Usage:** Minimal (< 50MB typical)
- **Concurrent Clients:** Supports multiple (HTTP/HTTPS)

## Platform Support

| Platform | Media Players        | Status      |
|----------|---------------------|-------------|
| Linux    | VLC, MPV, MPlayer   | ✓ Tested    |
| macOS    | Default (open)      | ✓ Ready     |
| Windows  | Default (startfile) | ✓ Ready     |

## File Formats

Supported extensions:
- `.mp4` `.mkv` `.avi` `.mov` `.wmv`
- `.flv` `.webm` `.m4v` `.mpg` `.mpeg`

To add more: Edit `MEDIA_EXTENSIONS` set in `media_server.py`

## Error Handling

1. **Missing directory:** Returns friendly error message
2. **No media files:** Returns empty list with notice
3. **File not found:** Returns error when playing
4. **No player:** Lists tried players in error message
5. **Network errors:** Client shows connection failures

## Dependencies

**Core:**
- `mcp>=1.0.0` - Model Context Protocol

**HTTP/HTTPS:**
- `starlette>=0.27.0` - ASGI framework
- `uvicorn>=0.23.0` - ASGI server
- `sse-starlette>=1.6.0` - Server-Sent Events

**Optional:**
- `anyio>=3.0.0` - Async I/O (usually included)

## Testing

**Scripts:**
- `test_basic.sh` - Environment validation
- `test_all_transports.sh` - Full transport testing

**Manual Testing:**
```bash
# Quick test
python media_client.py --protocol stdio --command list

# Full test
./test_all_transports.sh
```
