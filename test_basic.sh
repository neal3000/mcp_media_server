#!/bin/bash
# Basic test script for MCP Media Server

echo "=========================================="
echo "MCP Media Server - Basic Tests"
echo "=========================================="
echo ""

# Check Python
echo "1. Checking Python..."
python --version
echo ""

# Check dependencies
echo "2. Checking dependencies..."
python -c "import mcp; print('✓ mcp package installed')"
python -c "import starlette; print('✓ starlette package installed')"
python -c "import uvicorn; print('✓ uvicorn package installed')"
python -c "import sse_starlette; print('✓ sse-starlette package installed')"
echo ""

# Check media directory
echo "3. Checking media directory..."
if [ -d ~/Media/MOVIES ]; then
    echo "✓ Media directory exists: ~/Media/MOVIES"
    FILE_COUNT=$(find ~/Media/MOVIES -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.mov" \) 2>/dev/null | wc -l)
    echo "  Found $FILE_COUNT media files"
else
    echo "✗ Media directory does not exist"
    echo "  Run: mkdir -p ~/Media/MOVIES"
fi
echo ""

# Check for media player (Linux)
echo "4. Checking for media player..."
if command -v vlc &> /dev/null; then
    echo "✓ VLC found: $(which vlc)"
elif command -v mpv &> /dev/null; then
    echo "✓ MPV found: $(which mpv)"
elif command -v mplayer &> /dev/null; then
    echo "✓ MPlayer found: $(which mplayer)"
else
    echo "✗ No media player found"
    echo "  Install one: sudo apt install vlc"
fi
echo ""

# Test server syntax
echo "5. Testing server script syntax..."
python -m py_compile media_server.py && echo "✓ Server script syntax OK" || echo "✗ Server script has errors"
echo ""

echo "6. Testing client script syntax..."
python -m py_compile media_client.py && echo "✓ Client script syntax OK" || echo "✗ Client script has errors"
echo ""

echo "=========================================="
echo "Basic tests complete!"
echo ""
echo "To test the server manually:"
echo "  python media_server.py --help"
echo ""
echo "To test the client manually:"
echo "  python media_client.py --help"
echo "=========================================="
