#!/bin/bash
# Setup script for testing the MCP Media Server

echo "Setting up MCP Media Server test environment..."

# Create test media directory
echo "Creating test media directory: ~/Media/MOVIES"
mkdir -p ~/Media/MOVIES

# Check if any media files exist
if [ -z "$(ls -A ~/Media/MOVIES 2>/dev/null)" ]; then
    echo ""
    echo "Warning: No media files found in ~/Media/MOVIES"
    echo "Please add some video files (.mp4, .mkv, .avi, etc.) to test with."
    echo ""
fi

# Make scripts executable
chmod +x media_server.py
chmod +x media_client.py

echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Add media files to ~/Media/MOVIES"
echo "3. Run server: python media_server.py --transport stdio"
echo "4. Test client: python media_client.py --protocol stdio --command list"
