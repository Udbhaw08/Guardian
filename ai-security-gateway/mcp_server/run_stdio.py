import logging
import os
import sys

# Standard I/O MCP transport mandates that stdout contain ONLY JSON-RPC messages.
# Any logging or text printed to stdout will corrupt communication with Claude Desktop.
os.environ["AUTH_ENABLED"] = "false"
os.environ["MCP_STDIO"] = "true"
os.environ["LOG_STREAM"] = "stderr"

# Get the absolute path to the ai-security-gateway directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Change the current working directory to the project root
# This ensures that relative paths in .env (like POLICY_FILE_PATH) resolve correctly 
# even when Claude Desktop runs this script from a different directory.
os.chdir(project_root)

# Add the project root to the python path
sys.path.insert(0, project_root)

from mcp_server.app import mcp

# Pre-warm the prompt injection ML model at server startup
try:
    from detectors.prompt_injection import _get_model
    _get_model()
except Exception as exc:
    logging.error(f"Failed to preload model: {exc}")

# Re-route any root log handlers to stderr to prevent any library from leaking into stdout
for handler in logging.root.handlers[:]:
    if isinstance(handler, logging.StreamHandler):
        handler.setStream(sys.stderr)

if __name__ == "__main__":
    # Claude Desktop communicates via standard I/O rather than HTTP
    mcp.run(transport="stdio")
