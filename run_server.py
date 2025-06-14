#!/usr/bin/env python3
"""Convenience script to run the MCP Options Order Flow Server"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import and run the server
from src.mcp_server import main

if __name__ == "__main__":
    main()