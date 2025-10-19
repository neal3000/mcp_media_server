#!/bin/bash
# Comprehensive test script for all MCP Media Server transports

echo "=========================================="
echo "MCP Media Server - Transport Tests"
echo "=========================================="
echo ""

# Get the first movie filename for testing
FIRST_MOVIE=$(ls ~/Media/MOVIES/*.{mp4,mkv,avi,mov} 2>/dev/null | head -1 | xargs basename)

if [ -z "$FIRST_MOVIE" ]; then
    echo "ERROR: No media files found in ~/Media/MOVIES"
    exit 1
fi

echo "Using test movie: $FIRST_MOVIE"
echo ""

# Test 1: stdio - List
echo "=========================================="
echo "Test 1: stdio - List Movies"
echo "=========================================="
timeout 10 python media_client.py --protocol stdio --command list
if [ $? -eq 0 ]; then
    echo "✓ PASSED"
else
    echo "✗ FAILED"
fi
echo ""

# Test 2: stdio - Play
echo "=========================================="
echo "Test 2: stdio - Play Movie"
echo "=========================================="
echo "Note: This will launch VLC to play the movie"
read -p "Press Enter to continue or Ctrl+C to skip..."
timeout 5 python media_client.py --protocol stdio --command play --movie "$FIRST_MOVIE"
if [ $? -eq 0 ]; then
    echo "✓ PASSED"
else
    echo "✗ FAILED"
fi
echo ""

# Test 3: HTTP - Start server
echo "=========================================="
echo "Test 3: HTTP Transport"
echo "=========================================="
echo "Starting HTTP server..."
python media_server.py --transport http --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
sleep 3

echo "Testing HTTP list..."
timeout 10 python media_client.py --protocol http --url http://127.0.0.1:8000/sse --command list
LIST_RESULT=$?

echo ""
echo "Testing HTTP play..."
timeout 5 python media_client.py --protocol http --url http://127.0.0.1:8000/sse --command play --movie "$FIRST_MOVIE"
PLAY_RESULT=$?

# Cleanup
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

if [ $LIST_RESULT -eq 0 ] && [ $PLAY_RESULT -eq 0 ]; then
    echo "✓ PASSED"
else
    echo "✗ FAILED"
fi
echo ""

# Test 4: HTTPS (optional - requires certificates)
echo "=========================================="
echo "Test 4: HTTPS Transport (Optional)"
echo "=========================================="
if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
    echo "Certificates found, testing HTTPS..."

    echo "Starting HTTPS server..."
    python media_server.py --transport https --host 127.0.0.1 --port 8443 \
        --certfile cert.pem --keyfile key.pem &
    SERVER_PID=$!
    sleep 3

    echo "Testing HTTPS list..."
    timeout 10 python media_client.py --protocol https --url https://127.0.0.1:8443/sse --command list
    LIST_RESULT=$?

    # Cleanup
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null

    if [ $LIST_RESULT -eq 0 ]; then
        echo "✓ PASSED"
    else
        echo "✗ FAILED"
    fi
else
    echo "SKIPPED (no certificates found)"
    echo "To test HTTPS, generate certificates with:"
    echo "  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes"
fi
echo ""

echo "=========================================="
echo "All tests complete!"
echo "=========================================="
