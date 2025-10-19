# MCP Media Server - Usage Examples

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create media directory and add some video files
mkdir -p ~/Media/MOVIES
# Copy your video files to ~/Media/MOVIES
```

## Example 1: Testing with stdio Transport

**Terminal 1 - Start the server:**
```bash
python media_server.py --transport stdio
```

**Terminal 2 - List movies:**
```bash
python media_client.py --protocol stdio --command list
```

**Terminal 2 - Play a movie:**
```bash
python media_client.py --protocol stdio --command play --movie "your_movie.mp4"
```

## Example 2: Using HTTP Transport

**Terminal 1 - Start HTTP server:**
```bash
python media_server.py --transport http --host 0.0.0.0 --port 8000
```

**Terminal 2 - List movies:**
```bash
python media_client.py --protocol http --url http://localhost:8000/sse --command list
```

**Terminal 2 - Play a movie:**
```bash
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command play --movie "your_movie.mp4"
```

## Example 3: Using HTTPS Transport

**Step 1 - Generate self-signed certificate (for testing):**
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

**Terminal 1 - Start HTTPS server:**
```bash
python media_server.py --transport https --host 0.0.0.0 --port 8443 \
    --certfile cert.pem --keyfile key.pem
```

**Terminal 2 - List movies:**
```bash
python media_client.py --protocol https --url https://localhost:8443/sse --command list
```

**Terminal 2 - Play a movie:**
```bash
python media_client.py --protocol https --url https://localhost:8443/sse \
    --command play --movie "your_movie.mp4"
```

## Example 4: Claude Desktop Integration

**Edit your Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, or `%APPDATA%/Claude/claude_desktop_config.json` on Windows):

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

**Restart Claude Desktop**, then you can ask:
- "What movies are available?"
- "Play Inception.mp4"
- "List all the movies in my collection"

## Example 5: Remote Access via HTTP

Useful for controlling playback from another machine or n8n:

**On the media player machine (192.168.1.100):**
```bash
python media_server.py --transport http --host 0.0.0.0 --port 8000
```

**From another machine on the same network:**
```bash
# List movies
python media_client.py --protocol http --url http://192.168.1.100:8000/sse --command list

# Play a movie
python media_client.py --protocol http --url http://192.168.1.100:8000/sse \
    --command play --movie "your_movie.mp4"
```

## Example 6: Testing with curl (HTTP endpoint)

**List available tools:**
```bash
curl -X POST http://localhost:8000/messages \
    -H "Content-Type: application/json" \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/list",
      "params": {}
    }'
```

## Example 7: n8n Workflow

Create an n8n workflow with these nodes:

1. **HTTP Request Node** (Initialize connection):
   - Method: GET
   - URL: `http://your-server:8000/sse`

2. **HTTP Request Node** (List movies):
   - Method: POST
   - URL: `http://your-server:8000/messages`
   - Body:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/call",
       "params": {
         "name": "list_movies",
         "arguments": {}
       }
     }
     ```

3. **HTTP Request Node** (Play movie):
   - Method: POST
   - URL: `http://your-server:8000/messages`
   - Body:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "play_movie",
         "arguments": {
           "filename": "your_movie.mp4"
         }
       }
     }
     ```

## Example 8: Creating a Simple Web UI

You could create a simple HTML interface that connects to the HTTP endpoint:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Movie Player</title>
</head>
<body>
    <h1>Media Server Controller</h1>
    <button onclick="listMovies()">List Movies</button>
    <div id="movies"></div>

    <script>
        async function listMovies() {
            const response = await fetch('http://localhost:8000/messages', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    id: 1,
                    method: "tools/call",
                    params: {
                        name: "list_movies",
                        arguments: {}
                    }
                })
            });
            const data = await response.json();
            document.getElementById('movies').innerText = JSON.stringify(data, null, 2);
        }
    </script>
</body>
</html>
```

## Troubleshooting Examples

**Check if server is running (HTTP/HTTPS):**
```bash
# Should return connection info
curl -v http://localhost:8000/sse
```

**Test media directory access:**
```bash
ls -la ~/Media/MOVIES
```

**Check for media player:**
```bash
# Linux
which vlc mpv mplayer

# macOS
which open

# Test VLC
vlc --version
```

**Debug client connection:**
```bash
# Add verbose output (modify client to enable debug logging)
python media_client.py --protocol stdio --command list --verbose
```

## Performance Testing

**Test with multiple concurrent clients (HTTP):**
```bash
# Terminal 1
python media_client.py --protocol http --url http://localhost:8000/sse --command list &

# Terminal 2
python media_client.py --protocol http --url http://localhost:8000/sse --command list &

# Terminal 3
python media_client.py --protocol http --url http://localhost:8000/sse --command list &

# Wait for all to complete
wait
```

## Integration with Automation

**Bash script to play random movie:**
```bash
#!/bin/bash
# play_random_movie.sh

# Get list of movies and parse
MOVIES=$(python media_client.py --protocol stdio --command list | grep "^\s*[0-9]" | sed 's/^[0-9]*\. //')

# Pick a random one
RANDOM_MOVIE=$(echo "$MOVIES" | shuf -n 1)

# Play it
python media_client.py --protocol stdio --command play --movie "$RANDOM_MOVIE"
```

**Python script for scheduled playback:**
```python
#!/usr/bin/env python3
import schedule
import subprocess
import time

def play_movie():
    subprocess.run([
        "python", "media_client.py",
        "--protocol", "stdio",
        "--command", "play",
        "--movie", "daily_show.mp4"
    ])

# Play every day at 8 PM
schedule.every().day.at("20:00").do(play_movie)

while True:
    schedule.run_pending()
    time.sleep(60)
```
