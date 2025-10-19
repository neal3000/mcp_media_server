# Quick Command Reference

## Basic Commands

```bash
# List all movies
python media_client.py --protocol stdio --command list

# Play a movie
python media_client.py --protocol stdio --command play --movie "filename.mp4"

# Play with loop
python media_client.py --protocol stdio --command play --movie "filename.mp4" --loop
```

## Playback Control

```bash
# Pause/Resume
python media_client.py --protocol stdio --command pause

# Stop
python media_client.py --protocol stdio --command stop

# Restart from beginning
python media_client.py --protocol stdio --command restart
```

## Seeking

```bash
# Forward (default 10 seconds)
python media_client.py --protocol stdio --command seek-forward

# Forward custom amount
python media_client.py --protocol stdio --command seek-forward --seconds 30

# Backward (default 10 seconds)
python media_client.py --protocol stdio --command seek-backward

# Backward custom amount
python media_client.py --protocol stdio --command seek-backward --seconds 15
```

## Chapter Navigation

```bash
# Next chapter/scene
python media_client.py --protocol stdio --command next-chapter

# Previous chapter/scene
python media_client.py --protocol stdio --command previous-chapter
```

## Loop Control

```bash
# Toggle loop on/off
python media_client.py --protocol stdio --command toggle-loop
```

## HTTP Examples

Replace `stdio` with HTTP URL:

```bash
# All commands work with HTTP
python media_client.py --protocol http --url http://localhost:8000/sse \
    --command <command> [options]
```

## Server Commands

```bash
# Start stdio server
python media_server.py --transport stdio

# Start HTTP server
python media_server.py --transport http --host 0.0.0.0 --port 8000

# Start HTTPS server
python media_server.py --transport https --host 0.0.0.0 --port 8443 \
    --certfile cert.pem --keyfile key.pem
```

## Complete Syntax

```
python media_client.py \
    --protocol {stdio|http|https} \
    [--url <url>] \
    --command {list|play|pause|stop|seek-forward|seek-backward|next-chapter|previous-chapter|toggle-loop|restart} \
    [--movie <filename>] \
    [--loop] \
    [--seconds <n>]
```

## Tool Names (for MCP clients)

| Client Command | MCP Tool Name |
|----------------|---------------|
| `list` | `list_movies` |
| `play` | `play_movie` |
| `pause` | `pause_playback` |
| `stop` | `stop_playback` |
| `seek-forward` | `seek_forward` |
| `seek-backward` | `seek_backward` |
| `next-chapter` | `next_chapter` |
| `previous-chapter` | `previous_chapter` |
| `toggle-loop` | `toggle_loop` |
| `restart` | `restart_playback` |
