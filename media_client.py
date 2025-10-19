#!/usr/bin/env python3
"""
MCP Media Client - Connect to media server and control playback
Supports stdio, HTTP, and HTTPS transports
"""

import asyncio
import argparse
import sys
import json
from typing import Optional

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client


async def connect_stdio(server_script: str) -> ClientSession:
    """Connect to server using stdio transport"""
    server_params = StdioServerParameters(
        command="python",
        args=[server_script, "--transport", "stdio"],
    )

    stdio = stdio_client(server_params)
    stdio_read, stdio_write = await stdio.__aenter__()

    session = ClientSession(stdio_read, stdio_write)
    await session.__aenter__()

    return session, stdio


async def connect_http(url: str) -> ClientSession:
    """Connect to server using HTTP/HTTPS transport via SSE"""
    sse = sse_client(url)
    sse_read, sse_write = await sse.__aenter__()

    session = ClientSession(sse_read, sse_write)
    await session.__aenter__()

    return session, sse


async def list_movies(session: ClientSession):
    """List all available movies"""
    print("Fetching movie list...\n")

    result = await session.call_tool("list_movies", arguments={})

    for content in result.content:
        if hasattr(content, 'text'):
            print(content.text)


async def play_movie(session: ClientSession, filename: str, loop: bool = False):
    """Play a specific movie"""
    print(f"Requesting to play: {filename}")
    if loop:
        print("(with loop enabled)")
    print()

    result = await session.call_tool("play_movie", arguments={"filename": filename, "loop": loop})

    for content in result.content:
        if hasattr(content, 'text'):
            print(content.text)


async def control_playback(session: ClientSession, command: str, **kwargs):
    """Send a playback control command"""
    command_map = {
        "pause": "pause_playback",
        "stop": "stop_playback",
        "seek-forward": "seek_forward",
        "seek-backward": "seek_backward",
        "next-chapter": "next_chapter",
        "previous-chapter": "previous_chapter",
        "toggle-loop": "toggle_loop",
        "restart": "restart_playback"
    }

    tool_name = command_map.get(command)
    if not tool_name:
        print(f"Unknown command: {command}")
        return

    print(f"Sending command: {command}\n")

    result = await session.call_tool(tool_name, arguments=kwargs)

    for content in result.content:
        if hasattr(content, 'text'):
            print(content.text)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MCP Media Client - Control media server playback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List movies via stdio
  python media_client.py --protocol stdio --command list

  # Play movie via stdio
  python media_client.py --protocol stdio --command play --movie "example.mp4"

  # List movies via HTTP
  python media_client.py --protocol http --url http://localhost:8000/sse --command list

  # Play movie via HTTPS
  python media_client.py --protocol https --url https://localhost:8443/sse \\
      --command play --movie "example.mp4"
        """
    )

    parser.add_argument(
        "--protocol",
        choices=["stdio", "http", "https"],
        required=True,
        help="Protocol to use for connecting to server"
    )
    parser.add_argument(
        "--command",
        choices=["list", "play", "pause", "stop", "seek-forward", "seek-backward",
                 "next-chapter", "previous-chapter", "toggle-loop", "restart"],
        required=True,
        help="Command to execute"
    )
    parser.add_argument(
        "--movie",
        help="Movie filename to play (required for 'play' command)"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop the video (for 'play' command)"
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=10,
        help="Number of seconds to seek (for seek commands, default: 10)"
    )
    parser.add_argument(
        "--url",
        help="Server URL for HTTP/HTTPS (e.g., http://localhost:8000/sse)"
    )
    parser.add_argument(
        "--server-script",
        default="media_server.py",
        help="Path to server script for stdio (default: media_server.py)"
    )

    args = parser.parse_args()

    # Validation
    if args.command == "play" and not args.movie:
        parser.error("--movie is required when command is 'play'")

    if args.protocol in ["http", "https"] and not args.url:
        parser.error("--url is required for HTTP/HTTPS protocols")

    # Connect to server
    session = None
    transport = None

    try:
        print(f"Connecting to server via {args.protocol.upper()}...")

        if args.protocol == "stdio":
            session, transport = await connect_stdio(args.server_script)
        elif args.protocol in ["http", "https"]:
            session, transport = await connect_http(args.url)

        # Initialize the session
        await session.initialize()
        print(f"Connected successfully!\n")

        # Execute command
        if args.command == "list":
            await list_movies(session)
        elif args.command == "play":
            await play_movie(session, args.movie, args.loop)
        elif args.command in ["seek-forward", "seek-backward"]:
            await control_playback(session, args.command, seconds=args.seconds)
        else:
            await control_playback(session, args.command)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        # Cleanup
        if session:
            try:
                await session.__aexit__(None, None, None)
            except:
                pass

        if transport:
            try:
                await transport.__aexit__(None, None, None)
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
