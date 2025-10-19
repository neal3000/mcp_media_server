# MCP Media Server

A Model Context Protocol (MCP) server and client for listing and playing media files from `~/Media/MOVIES`. Supports stdio, HTTP, and HTTPS transports, compatible with Claude Desktop and n8n.

## Features

- **List Movies**: Browse all media files in your Movies directory
- **Play Movies**: Start playback using system default media player
- **Multiple Transports**: stdio (for Claude Desktop), HTTP, and HTTPS
- **Cross-Platform**: Works on Linux, macOS, and Windows

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install individually
pip install mcp starlette uvicorn sse-starlette
```

## Quick Start

### Server

**stdio (for Claude Desktop):**
```bash
python media_server.py --transport stdio
```

**HTTP:**
```bash
python media_server.py --transport http --host 0.0.0.0 --port 8000
```

**HTTPS:**
```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Start server
python media_server.py --transport https --host 0.0.0.0 --port 8443 \
    --certfile cert.pem --keyfile key.pem
```

### Client

**List movies via stdio:**
```bash
python media_client.py --protocol stdio --command list
```

**Play movie via stdio:**
```bash
python media_client.py --protocol stdio --command play --movie "example.mp4"
```

**List movies via HTTP:**
```bash
python media_client.py --protocol http --url http://localhost:8000/sse --command list
```

**Play movie via HTTPS:**
```bash
python media_client.py --protocol https --url https://localhost:8443/sse \
    --command play --movie "example.mp4"
```

## Configuration

### Media Directory

By default, the server looks for media files in `~/Media/MOVIES`. To change this, edit the `MEDIA_DIR` variable in `media_server.py`:

```python
MEDIA_DIR = Path.home() / "Media" / "MOVIES"
```

### Supported File Types

The following video formats are supported:
- .mp4, .mkv, .avi, .mov, .wmv, .flv, .webm, .m4v, .mpg, .mpeg

To add more formats, edit the `MEDIA_EXTENSIONS` set in `media_server.py`.

## Claude Desktop Integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

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

## n8n Integration

For n8n, use the HTTP or HTTPS transport:

1. Start the server with HTTP/HTTPS transport
2. In n8n, use the HTTP Request node to connect to `http://your-server:8000/sse`
3. Use POST requests to `/messages` endpoint for MCP communication

## Media Player Requirements

The server will automatically detect and use available media players:

**Linux:**
- VLC (`vlc`)
- MPV (`mpv`)
- MPlayer (`mplayer`)
- Or system default (`xdg-open`)

**macOS:**
- Uses `open` command (system default player)

**Windows:**
- Uses `os.startfile()` (system default player)

### Install a Player (Linux)

```bash
# Ubuntu/Debian
sudo apt install vlc

# Fedora
sudo dnf install vlc

# Arch
sudo pacman -S vlc
```

## API Reference

### Tools

#### list_movies

Lists all media files in the Movies directory.

**Arguments:** None

**Returns:** List of movies with name, path, size, and file type

**Example:**
```json
{
  "name": "list_movies",
  "arguments": {}
}
```

#### play_movie

Plays a specific movie using the system's default media player.

**Arguments:**
- `filename` (string, required): Name of the movie file

**Returns:** Status message indicating success or error

**Example:**
```json
{
  "name": "play_movie",
  "arguments": {
    "filename": "example.mp4"
  }
}
```

## Server Command-Line Options

```
usage: media_server.py [-h] [--transport {stdio,http,https}] [--host HOST]
                       [--port PORT] [--certfile CERTFILE] [--keyfile KEYFILE]

optional arguments:
  --transport {stdio,http,https}
                        Transport protocol to use (default: stdio)
  --host HOST          Host to bind to for HTTP/HTTPS (default: 127.0.0.1)
  --port PORT          Port to bind to for HTTP/HTTPS (default: 8000)
  --certfile CERTFILE  SSL certificate file for HTTPS
  --keyfile KEYFILE    SSL key file for HTTPS
```

## Client Command-Line Options

```
usage: media_client.py [-h] --protocol {stdio,http,https} --command {list,play}
                       [--movie MOVIE] [--url URL] [--server-script SERVER_SCRIPT]

optional arguments:
  --protocol {stdio,http,https}
                        Protocol to use for connecting to server
  --command {list,play}
                        Command to execute (list or play)
  --movie MOVIE        Movie filename to play (required for 'play' command)
  --url URL            Server URL for HTTP/HTTPS (e.g., http://localhost:8000/sse)
  --server-script SERVER_SCRIPT
                        Path to server script for stdio (default: media_server.py)
```

## Troubleshooting

### No media player found

Install VLC or another supported media player:
```bash
sudo apt install vlc  # Linux
brew install vlc      # macOS
```

### Connection errors with HTTP/HTTPS

- Check that the server is running
- Verify the URL includes `/sse` endpoint
- For HTTPS, ensure certificate files are valid

### Permission errors

Ensure the `~/Media/MOVIES` directory exists and is readable:
```bash
mkdir -p ~/Media/MOVIES
chmod 755 ~/Media/MOVIES
```

## Security Notes

- The server only accesses files in the configured media directory
- For production use with HTTPS, use proper SSL certificates (not self-signed)
- Consider restricting the `--host` parameter to specific IPs in production
- The server does not modify or delete any files

## License

MIT License - Feel free to use and modify as needed.
