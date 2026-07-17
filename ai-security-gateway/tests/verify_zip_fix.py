import warnings, sys, os
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
os.environ["AUTH_ENABLED"] = "false"

from mcp_server.app import app
print("Server imports OK - app loaded successfully")

from mcp_server.tools.scan_document_tool import _handle_zip_listing
print("Tool imports OK")

# Test 1: ZIP with .env at root — should BLOCK
r = _handle_zip_listing("README.md\nsrc/app.py\n.env\nbackend/.env.production", "project.zip")
print(f"Test 1 (root .env): {r['decision']} | {r['stealth_flags']}")

# Test 2: Clean ZIP — should ALLOW
r2 = _handle_zip_listing("README.md\nsrc/app.py\nsrc/utils.py", "clean.zip")
print(f"Test 2 (clean):     {r2['decision']} | {r2['reason'][:50]}")

# Test 3: ZIP with nested env file (no dot prefix) — should BLOCK
r3 = _handle_zip_listing("project/\nproject/src/main.py\nproject/env", "myapp.zip")
print(f"Test 3 (plain env): {r3['decision']} | {r3['stealth_flags']}")
