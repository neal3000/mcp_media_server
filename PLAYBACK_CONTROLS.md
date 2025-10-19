# MPV Playback Controls

The media server now includes full playback control for MPV using IPC (Inter-Process Communication). This allows you to control a running MPV instance remotely.

## How It Works

When you play a movie with MPV, the server starts it with an IPC socket at `/tmp/mpv-ipc-socket`. This socket allows sending JSON-RPC commands to control playback.

## Available Commands

### Basic Playback

#### play
```bash
# Play a movie (with MPV IPC enabled)
python media_client.py --protocol stdio --command play --movie "Airplane!.mp4"

# Play with loop enabled
python media_client.py --protocol stdio --command play --movie "Airplane!.mp4" --loop
```

#### pause
```bash
# Toggle pause/unpause
python media_client.py --protocol stdio --command pause
```

#### stop
```bash
# Stop playback and quit MPV
python media_client.py --protocol stdio --command stop
```

### Seeking

#### seek-forward
```bash
# Skip forward 10 seconds (default)
python media_client.py --protocol stdio --command seek-forward

# Skip forward 30 seconds
python media_client.py --protocol stdio --command seek-forward --seconds 30
```

#### seek-backward
```bash
# Skip backward 10 seconds (default)
python media_client.py --protocol stdio --command seek-backward

# Skip backward 15 seconds
python media_client.py --protocol stdio --command seek-backward --seconds 15
```

#### restart
```bash
# Restart from beginning
python media_client.py --protocol stdio --command restart
```

### Chapter Navigation

For videos with chapters (like DVDs or structured videos):

#### next-chapter
```bash
# Jump to next chapter/scene
python media_client.py --protocol stdio --command next-chapter
```

#### previous-chapter
```bash
# Jump to previous chapter/scene
python media_client.py --protocol stdio --command previous-chapter
```

### Loop Control

#### toggle-loop
```bash
# Toggle loop mode on/off
python media_client.py --protocol stdio --command toggle-loop
```

## HTTP/HTTPS Control

All commands work over HTTP/HTTPS as well:

```bash
# Start server
python media_server.py --transport http --host 0.0.0.0 --port 8000

# Play a movie
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command play --movie "Airplane!.mp4"

# Pause
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command pause

# Seek forward
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command seek-forward --seconds 30
```

## Complete Command Reference

| Command | Arguments | Description |
|---------|-----------|-------------|
| `list` | None | List all available movies |
| `play` | `--movie <file>` `--loop` (optional) | Play a movie |
| `pause` | None | Toggle pause/play |
| `stop` | None | Stop and quit |
| `seek-forward` | `--seconds <n>` (optional, default: 10) | Skip forward |
| `seek-backward` | `--seconds <n>` (optional, default: 10) | Skip backward |
| `next-chapter` | None | Next chapter/scene |
| `previous-chapter` | None | Previous chapter/scene |
| `toggle-loop` | None | Toggle loop mode |
| `restart` | None | Restart from beginning |

## Example Usage Scenarios

### Remote Movie Night

```bash
# On the media server (Raspberry Pi, etc.)
python media_server.py --transport http --host 0.0.0.0 --port 8000

# From your phone/laptop/another device
# List movies
python media_client.py --protocol http --url http://192.168.1.100:8000/sse --command list

# Start the movie
python media_client.py --protocol http --url http://192.168.1.100:8000/sse \
    --command play --movie "The Fantastic 4 First Steps.mp4"

# Pause for bathroom break
python media_client.py --protocol http --url http://192.168.1.100:8000/sse --command pause

# Resume
python media_client.py --protocol http --url http://192.168.1.100:8000/sse --command pause

# Skip opening credits
python media_client.py --protocol http --url http://192.168.1.100:8000/sse \
    --command seek-forward --seconds 60

# Rewind to catch a line
python media_client.py --protocol http --url http://192.168.1.100:8000/sse \
    --command seek-backward --seconds 5

# Stop when done
python media_client.py --protocol http --url http://192.168.1.100:8000/sse --command stop
```

### Automated Playback

```bash
#!/bin/bash
# play_movie_sequence.sh - Play a sequence with control

# Start first movie
python media_client.py --protocol stdio --command play --movie "Movie1.mp4"

sleep 10

# Skip intro
python media_client.py --protocol stdio --command seek-forward --seconds 30

# Wait for it to finish (implement your own wait logic)
# ...

# Play next movie
python media_client.py --protocol stdio --command play --movie "Movie2.mp4"
```

### Claude Desktop Integration

With Claude Desktop, you can use natural language:

```
User: Play Airplane
Claude: [uses play_movie tool]

User: Pause it
Claude: [uses pause_playback tool]

User: Skip forward 30 seconds
Claude: [uses seek_forward tool with seconds: 30]

User: Go back to the beginning
Claude: [uses restart_playback tool]

User: Stop playback
Claude: [uses stop_playback tool]
```

## MPV Commands Reference

The server uses these MPV IPC commands:

| Tool | MPV Command | Effect |
|------|-------------|--------|
| `pause_playback` | `cycle pause` | Toggle pause state |
| `stop_playback` | `quit` | Exit MPV |
| `seek_forward` | `seek <n> relative` | Seek forward |
| `seek_backward` | `seek -<n> relative` | Seek backward |
| `restart_playback` | `seek 0 absolute` | Jump to start |
| `next_chapter` | `add chapter 1` | Next chapter |
| `previous_chapter` | `add chapter -1` | Previous chapter |
| `toggle_loop` | `cycle loop-file` | Toggle loop mode |

## Advanced: Direct Socket Communication

You can also communicate directly with the MPV socket:

```bash
# Using echo and socat
echo '{"command": ["cycle", "pause"]}' | socat - /tmp/mpv-ipc-socket

# Get current position
echo '{"command": ["get_property", "time-pos"]}' | socat - /tmp/mpv-ipc-socket
```

## Troubleshooting

### "MPV is not running or IPC socket not found"

**Problem:** Trying to control playback when no movie is playing.

**Solution:** Start playing a movie first:
```bash
python media_client.py --protocol stdio --command play --movie "YourMovie.mp4"
```

### Controls don't work with VLC

**Problem:** VLC doesn't support the same IPC mechanism.

**Solution:** The server automatically uses MPV when available. Make sure MPV is installed:
```bash
sudo apt install mpv  # Linux
brew install mpv      # macOS
```

### Socket permission errors

**Problem:** Can't connect to `/tmp/mpv-ipc-socket`.

**Solution:** The socket is created with user-only permissions. Run the client as the same user that started MPV.

## Platform Support

| Platform | MPV IPC Support | Fallback |
|----------|----------------|----------|
| Linux | ✓ Yes | VLC, MPlayer |
| macOS | ✓ Yes | open command |
| Windows | ✓ Yes | startfile |

## Future Enhancements

Possible additions:
- Volume control
- Subtitle track selection
- Audio track selection
- Playback speed control
- Screenshot capture
- Playlist management
- Query current position/duration
- Query playing status

To request features, modify media_server.py:line233 (@app.list_tools) and add new tool definitions.
