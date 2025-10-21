#!/usr/bin/env python3
"""
MCP Media Server - Lists and plays media files from ~/Media/MOVIES
Supports stdio, HTTP, and HTTPS transports
Compatible with Claude and n8n
"""

import os
import sys
import asyncio
import argparse
import subprocess
import socket
import json
import tempfile
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# For HTTP/HTTPS support
try:
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import Response
    from mcp.server.sse import SseServerTransport
    import uvicorn
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    print("Warning: starlette/uvicorn not available. HTTP/HTTPS transport disabled.", file=sys.stderr)


# Initialize the MCP server
app = Server("media-server")

# Media directory path
MEDIA_DIR = Path.home() / "Media" / "MOVIES"

# Supported media file extensions
MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

# MPV IPC socket path
MPV_SOCKET = Path(tempfile.gettempdir()) / "mpv-ipc-socket"

# Track current MPV process and playing file
current_mpv_process = None
currently_playing_file = None


def fuzzy_match_filename(query: str, filename: str) -> float:
    """
    Calculate fuzzy match score between query and filename.
    Returns a score between 0.0 (no match) and 1.0 (perfect match).
    """
    # Remove extension for matching
    name_without_ext = Path(filename).stem.lower()
    query_lower = query.lower()
    
    # Exact match (case insensitive)
    if query_lower in name_without_ext or name_without_ext in query_lower:
        return 1.0
    
    # Sequence matcher for similarity
    return SequenceMatcher(None, query_lower, name_without_ext).ratio()


def find_best_match(query: str, media_files: list) -> Optional[dict]:
    """
    Find the best matching media file for the given query using fuzzy matching.
    Returns the file with the highest match score, or None if no good match found.
    """
    if not media_files:
        return None
    
    best_match = None
    best_score = 0.0
    threshold = 0.3  # Minimum similarity threshold
    
    for file_info in media_files:
        score = fuzzy_match_filename(query, file_info['name'])
        if score > best_score and score >= threshold:
            best_score = score
            best_match = file_info
    
    return best_match


def stop_current_playback() -> tuple[bool, str]:
    """
    Stop the currently playing media file if any.
    """
    global current_mpv_process, currently_playing_file
    
    if current_mpv_process is None:
        return True, "No media currently playing"
    
    try:
        # Try to gracefully stop via IPC first
        if MPV_SOCKET.exists():
            success, message = send_mpv_command(["quit"], expect_response=False)
            if success:
                # Give it a moment to close gracefully
                try:
                    current_mpv_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't close gracefully
                    current_mpv_process.kill()
                    current_mpv_process.wait()
        else:
            # Force kill if no IPC socket
            current_mpv_process.kill()
            current_mpv_process.wait()
        
        current_mpv_process = None
        currently_playing_file = None
        return True, "Playback stopped"
        
    except Exception as e:
        # Fallback: try to kill the process
        try:
            if current_mpv_process:
                current_mpv_process.kill()
                current_mpv_process.wait()
        except:
            pass
        finally:
            current_mpv_process = None
            currently_playing_file = None
        
        return False, f"Error stopping playback: {str(e)}"


def send_mpv_command(command: list, expect_response: bool = True) -> tuple[bool, str]:
    """
    Send a command to MPV via IPC socket

    Args:
        command: List containing the command and arguments
        expect_response: Whether to wait for a response

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not MPV_SOCKET.exists():
        return False, "MPV is not running or IPC socket not found"

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(MPV_SOCKET))

        # Send command as JSON-RPC
        request = {"command": command}
        sock.sendall((json.dumps(request) + "\n").encode('utf-8'))

        if expect_response:
            # Read response
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in response:
                    break

            sock.close()

            if response:
                result = json.loads(response.decode('utf-8'))
                if result.get('error') == 'success':
                    return True, f"Command executed: {' '.join(map(str, command))}"
                else:
                    return False, f"MPV error: {result.get('error', 'unknown')}"
        else:
            sock.close()
            return True, f"Command sent: {' '.join(map(str, command))}"

    except FileNotFoundError:
        return False, "MPV IPC socket not found"
    except ConnectionRefusedError:
        return False, "Could not connect to MPV"
    except Exception as e:
        return False, f"Error communicating with MPV: {str(e)}"


def get_media_files():
    """Get list of media files in the MOVIES directory"""
    if not MEDIA_DIR.exists():
        return []

    media_files = []
    try:
        for item in MEDIA_DIR.iterdir():
            if item.is_file() and item.suffix.lower() in MEDIA_EXTENSIONS:
                media_files.append({
                    'name': item.name,
                    'path': str(item),
                    'size': item.stat().st_size,
                    'extension': item.suffix
                })
    except Exception as e:
        print(f"Error scanning directory: {e}", file=sys.stderr)

    return sorted(media_files, key=lambda x: x['name'])


def play_media_file(filename: str, loop: bool = False) -> tuple[bool, str]:
    """
    Play a media file using MPV with IPC control

    Args:
        filename: Name of the file to play
        loop: Whether to loop the video

    Returns:
        Tuple of (success: bool, message: str)
    """
    global current_mpv_process, currently_playing_file

    file_path = MEDIA_DIR / filename

    if not file_path.exists():
        return False, f"File not found: {filename}"

    if file_path.suffix.lower() not in MEDIA_EXTENSIONS:
        return False, f"Not a supported media file: {filename}"

    # Stop currently playing file if any
    if current_mpv_process is not None:
        stop_success, stop_message = stop_current_playback()
        if not stop_success:
            print(f"Warning: Could not stop previous playback: {stop_message}", file=sys.stderr)

    try:
        # Remove old socket if it exists
        if MPV_SOCKET.exists():
            MPV_SOCKET.unlink()

        # Detect platform and use appropriate player
        if sys.platform == 'linux':
            # Try MPV first with IPC support
            if subprocess.run(['which', 'mpv'], capture_output=True).returncode == 0:
                mpv_args = [
                    'mpv',
                    f'--input-ipc-server={MPV_SOCKET}',
                    str(file_path)
                ]
                if loop:
                    mpv_args.insert(1, '--loop=inf')

                current_mpv_process = subprocess.Popen(
                    mpv_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                currently_playing_file = filename
                return True, f"Playing {filename} with MPV (IPC enabled)"

            # Fallback to other players
            players = ['vlc', 'mplayer', 'xdg-open']
            for player in players:
                if subprocess.run(['which', player], capture_output=True).returncode == 0:
                    subprocess.Popen([player, str(file_path)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    currently_playing_file = filename
                    return True, f"Playing {filename} with {player} (no IPC control)"
            return False, "No media player found (tried: mpv, vlc, mplayer, xdg-open)"

        elif sys.platform == 'darwin':  # macOS
            # Try MPV on macOS
            if subprocess.run(['which', 'mpv'], capture_output=True).returncode == 0:
                mpv_args = [
                    'mpv',
                    f'--input-ipc-server={MPV_SOCKET}',
                    str(file_path)
                ]
                if loop:
                    mpv_args.insert(1, '--loop=inf')

                current_mpv_process = subprocess.Popen(
                    mpv_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                currently_playing_file = filename
                return True, f"Playing {filename} with MPV (IPC enabled)"
            else:
                subprocess.Popen(['open', str(file_path)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                currently_playing_file = filename
                return True, f"Playing {filename} (no IPC control)"

        elif sys.platform == 'win32':  # Windows
            # Try MPV on Windows
            if subprocess.run(['where', 'mpv'], capture_output=True).returncode == 0:
                mpv_args = [
                    'mpv',
                    f'--input-ipc-server={MPV_SOCKET}',
                    str(file_path)
                ]
                if loop:
                    mpv_args.insert(1, '--loop=inf')

                current_mpv_process = subprocess.Popen(
                    mpv_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                currently_playing_file = filename
                return True, f"Playing {filename} with MPV (IPC enabled)"
            else:
                os.startfile(str(file_path))
                currently_playing_file = filename
                return True, f"Playing {filename} (no IPC control)"

        else:
            return False, f"Unsupported platform: {sys.platform}"

    except Exception as e:
        return False, f"Error playing file: {str(e)}"


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_movies",
            description=f"List all media files available in {MEDIA_DIR}. Returns name, path, size, and extension for each file.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="play_movie",
            description="Play a specific movie file using MPV with IPC control. Supports fuzzy matching by name and optional loop parameter. If another movie is playing, it will be stopped first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the movie file to play (e.g., 'movie.mp4') or a partial name for fuzzy matching (e.g., 'superman' will match 'Superman.mp4')"
                    },
                    "loop": {
                        "type": "boolean",
                        "description": "Whether to loop the video infinitely (default: false)"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="pause_playback",
            description="Pause or unpause the currently playing video in MPV. Toggles between pause and play.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="stop_playback",
            description="Stop playback and quit MPV.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="seek_forward",
            description="Skip forward in the video by a specified number of seconds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "Number of seconds to skip forward (default: 10)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="seek_backward",
            description="Skip backward in the video by a specified number of seconds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "Number of seconds to skip backward (default: 10)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="next_chapter",
            description="Jump to the next chapter or scene in the video.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="previous_chapter",
            description="Jump to the previous chapter or scene in the video.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="toggle_loop",
            description="Toggle loop mode on/off for the current video.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="restart_playback",
            description="Restart the video from the beginning.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_current_playing",
            description="Get the name of the currently playing media file, if any.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "list_movies":
        media_files = get_media_files()

        if not media_files:
            if not MEDIA_DIR.exists():
                return [TextContent(
                    type="text",
                    text=f"Media directory does not exist: {MEDIA_DIR}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"No media files found in {MEDIA_DIR}"
                )]

        # Format the response
        response = f"Found {len(media_files)} media file(s) in {MEDIA_DIR}:\n\n"
        for i, file in enumerate(media_files, 1):
            size_mb = file['size'] / (1024 * 1024)
            response += f"{i}. {file['name']}\n"
            response += f"   Path: {file['path']}\n"
            response += f"   Size: {size_mb:.2f} MB\n"
            response += f"   Type: {file['extension']}\n\n"

        return [TextContent(type="text", text=response)]

    elif name == "play_movie":
        filename_query = arguments.get("filename")
        loop = arguments.get("loop", False)

        if not filename_query:
            return [TextContent(
                type="text",
                text="Error: filename parameter is required"
            )]

        media_files = get_media_files()
        
        # First try exact match
        exact_match = None
        for file_info in media_files:
            if file_info['name'].lower() == filename_query.lower():
                exact_match = file_info
                break
        
        if exact_match:
            # Exact match found
            success, message = play_media_file(exact_match['name'], loop)
            return [TextContent(type="text", text=message)]
        
        # Try fuzzy matching
        best_match = find_best_match(filename_query, media_files)
        
        if best_match:
            success, message = play_media_file(best_match['name'], loop)
            match_score = fuzzy_match_filename(filename_query, best_match['name'])
            message += f"\n\nNote: Matched '{best_match['name']}' from query '{filename_query}' (confidence: {match_score:.2f})"
            return [TextContent(type="text", text=message)]
        else:
            # No match found
            available_files = "\n".join([f"- {f['name']}" for f in media_files])
            return [TextContent(
                type="text",
                text=f"No media file found matching '{filename_query}'. Available files:\n{available_files}"
            )]

    elif name == "pause_playback":
        success, message = send_mpv_command(["cycle", "pause"])
        return [TextContent(type="text", text=message)]

    elif name == "stop_playback":
        success, message = stop_current_playback()
        return [TextContent(type="text", text=message)]

    elif name == "seek_forward":
        seconds = arguments.get("seconds", 10)
        success, message = send_mpv_command(["seek", seconds, "relative"])
        return [TextContent(type="text", text=message)]

    elif name == "seek_backward":
        seconds = arguments.get("seconds", 10)
        success, message = send_mpv_command(["seek", -seconds, "relative"])
        return [TextContent(type="text", text=message)]

    elif name == "next_chapter":
        success, message = send_mpv_command(["add", "chapter", 1])
        return [TextContent(type="text", text=message)]

    elif name == "previous_chapter":
        success, message = send_mpv_command(["add", "chapter", -1])
        return [TextContent(type="text", text=message)]

    elif name == "toggle_loop":
        success, message = send_mpv_command(["cycle", "loop-file"])
        return [TextContent(type="text", text=message)]

    elif name == "restart_playback":
        success, message = send_mpv_command(["seek", 0, "absolute"])
        return [TextContent(type="text", text=message)]

    elif name == "get_current_playing":
        if currently_playing_file:
            return [TextContent(
                type="text",
                text=f"Currently playing: {currently_playing_file}"
            )]
        else:
            return [TextContent(
                type="text",
                text="No media is currently playing"
            )]

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def run_stdio():
    """Run the server using stdio transport"""
    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )


def create_sse_app():
    """Create Starlette app for SSE transport (HTTP/HTTPS)"""
    if not HTTP_AVAILABLE:
        raise RuntimeError("HTTP transport not available. Install: pip install starlette uvicorn sse-starlette")

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options()
            )
        return Response()

    starlette_app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    return starlette_app


def run_http_server(host: str, port: int, use_ssl: bool = False, certfile: str = None, keyfile: str = None):
    """Run the server using HTTP/HTTPS with SSE transport"""
    if not HTTP_AVAILABLE:
        print("Error: HTTP transport not available. Install: pip install starlette uvicorn sse-starlette", file=sys.stderr)
        sys.exit(1)

    starlette_app = create_sse_app()

    config = {
        "app": starlette_app,
        "host": host,
        "port": port,
    }

    if use_ssl:
        if not certfile or not keyfile:
            print("Error: SSL enabled but certificate/key files not provided", file=sys.stderr)
            sys.exit(1)
        config["ssl_certfile"] = certfile
        config["ssl_keyfile"] = keyfile
        protocol = "https"
    else:
        protocol = "http"

    print(f"Starting MCP Media Server on {protocol}://{host}:{port}", file=sys.stderr)
    print(f"SSE endpoint: {protocol}://{host}:{port}/sse", file=sys.stderr)
    print(f"Media directory: {MEDIA_DIR}", file=sys.stderr)

    uvicorn.run(**config)


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="MCP Media Server - List and play media files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio (for Claude Desktop, etc.)
  python media_server.py --transport stdio

  # Run with HTTP
  python media_server.py --transport http --host 0.0.0.0 --port 8000

  # Run with HTTPS
  python media_server.py --transport https --host 0.0.0.0 --port 8443 \\
      --certfile cert.pem --keyfile key.pem
        """
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "https"],
        default="http",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP/HTTPS (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to bind to for HTTP/HTTPS (default: 8000)"
    )
    parser.add_argument(
        "--certfile",
        help="SSL certificate file for HTTPS"
    )
    parser.add_argument(
        "--keyfile",
        help="SSL key file for HTTPS"
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio())
    elif args.transport in ["http", "https"]:
        use_ssl = args.transport == "https"
        run_http_server(args.host, args.port, use_ssl, args.certfile, args.keyfile)


if __name__ == "__main__":
    main()

