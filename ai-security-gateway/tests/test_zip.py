import sys, os, base64, asyncio, io, zipfile, warnings
warnings.filterwarnings("ignore", category=UserWarning)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
os.environ["AUTH_ENABLED"] = "false"

from mcp_server.tools.scan_document_tool import handle_scan_document


async def main():
    # Test 1: ZIP with root-level .env
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("README.md", "# My Project")
        zf.writestr("src/main.py", 'print("hello")')
        zf.writestr(".env", "SECRET_KEY=supersecret\nDB_PASS=hunter2")
    b64 = base64.b64encode(buf.getvalue()).decode()
    r = await handle_scan_document(b64, "project.zip")
    print("--- Test 1: ZIP with root-level .env ---")
    print("Decision:", r["decision"])
    print("Sensitive files:", r["stealth_flags"])
    print("Reason:", r["reason"])

    print()

    # Test 2: Clean ZIP
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as zf:
        zf.writestr("README.md", "# Clean project")
        zf.writestr("src/app.py", 'print("safe")')
    b64_2 = base64.b64encode(buf2.getvalue()).decode()
    r2 = await handle_scan_document(b64_2, "clean.zip")
    print("--- Test 2: Clean ZIP ---")
    print("Decision:", r2["decision"])
    print("Reason:", r2["reason"])

    print()

    # Test 3: ZIP with nested .env.production
    buf3 = io.BytesIO()
    with zipfile.ZipFile(buf3, "w") as zf:
        zf.writestr("frontend/index.html", "<html/>")
        zf.writestr("backend/.env.production", "DATABASE_URL=postgres://prod:password@db:5432/app")
    b64_3 = base64.b64encode(buf3.getvalue()).decode()
    r3 = await handle_scan_document(b64_3, "myapp.zip")
    print("--- Test 3: ZIP with nested .env.production ---")
    print("Decision:", r3["decision"])
    print("Sensitive files:", r3["stealth_flags"])
    print("Reason:", r3["reason"])


asyncio.run(main())
