import warnings, sys, os, base64, asyncio
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["AUTH_ENABLED"] = "false"

with open("tests/images/invoice_injection.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

from mcp_server.tools.scan_document_tool import handle_scan_document

r = asyncio.run(handle_scan_document(b64, "invoice_injection.png"))
print("Decision:", r["decision"])
print("Matched: ", r["matched_types"])
print("Confidence:", r["confidence"])
print("Reason:  ", r["reason"][:160])
