# Quick Start Guide

## Test Your Setup (30 seconds)

```bash
# 1. Run basic tests
./test_basic.sh

# 2. List your movies (using stdio)
python media_client.py --protocol stdio --command list

# 3. Play a movie (replace with your actual filename)
python media_client.py --protocol stdio --command play --movie "your_movie.mp4"
```

## HTTP Server (for remote access)

**Terminal 1 - Start server:**
```bash
python media_server.py --transport http --host 0.0.0.0 --port 8000
```

**Terminal 2 - Test client:**
```bash
# List movies
python media_client.py --protocol http --url http://localhost:8000/sse --command list

# Play a movie
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command play --movie "your_movie.mp4"
```

## For Claude Desktop

1. Edit your config file:
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2. Add this configuration:
```json
{
  "mcpServers": {
    "media-server": {
      "command": "python",
      "args": [
        "/home/nkatz/Development/mcp2/media_server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

3. Restart Claude Desktop

4. Ask Claude: "What movies are available?" or "Play moviename.mp4"

## Troubleshooting

**No movies found?**
```bash
# Make sure the directory exists and has media files
ls -la ~/Media/MOVIES
```

**Can't play movies?**
```bash
# Install VLC on Linux
sudo apt install vlc

# Install VLC on macOS
brew install vlc
```

**Connection errors with HTTP?**
```bash
# Make sure the server is running in another terminal
# Check the URL includes /sse at the end
```

For more examples, see `EXAMPLES.md` and `README.md`
