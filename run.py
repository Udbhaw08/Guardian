#!/usr/bin/env python3
"""
run.py
------
Unified runner script for the Guardian project.
Starts the following components concurrently:
1. Backend REST API (Port 8001)
2. MCP Server (Port 8000)
3. Frontend Dev Server (Port 5173)
4. Ngrok tunnel on a chosen port (Default: 8000)

Handles clean shutdown of all child processes on Ctrl+C.
"""

import sys
import os
import subprocess
import threading
import signal
import time
import argparse
import urllib.request
import json
import socket
import shutil

# ANSI colors for nice logging
COLOR_RESET = "\033[0m"
COLOR_API = "\033[96m"       # Cyan
COLOR_MCP = "\033[95m"       # Magenta
COLOR_FRONTEND = "\033[92m"  # Green
COLOR_NGROK = "\033[93m"     # Yellow
COLOR_SYSTEM = "\033[91m"    # Red
COLOR_BOLD = "\033[1m"

def print_log(prefix, message, color):
    """Print formatted logs with prefixes and colors."""
    if sys.stdout.isatty():
        print(f"{color}[{prefix}]{COLOR_RESET} {message}")
    else:
        print(f"[{prefix}] {message}")

def check_port(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error:
            return True

def get_python_executable():
    """Locate the Python executable in the virtual environment or fallback to system python."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(root_dir, ".venv")
    
    if os.path.exists(venv_dir):
        if sys.platform == "win32":
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(venv_dir, "bin", "python")
        
        if os.path.exists(python_exe):
            return python_exe
            
    return sys.executable

def stream_output(process, prefix, color):
    """Read standard output from a process and log it line-by-line."""
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            print_log(prefix, line.strip(), color)
    except Exception as e:
        print_log("System", f"Error reading output from {prefix}: {e}", COLOR_SYSTEM)

def get_ngrok_url():
    """Query local ngrok client API to retrieve the active public tunnel URL."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=1) as response:
            data = json.loads(response.read().decode())
            tunnels = data.get("tunnels", [])
            if tunnels:
                return tunnels[0].get("public_url")
    except Exception:
        pass
    return None

def monitor_ngrok(ngrok_port, stop_event):
    """Poll ngrok local API to display the public URL once established."""
    print_log("Ngrok Monitor", "Waiting for ngrok tunnel to establish...", COLOR_NGROK)
    for _ in range(15):
        if stop_event.is_set():
            return
        time.sleep(1)
        url = get_ngrok_url()
        if url:
            banner = f"""
========================================================================
   🚀  SERVICES ARE RUNNING AND EXPOSED VIA NGROK!
   
   🔗  Ngrok Public URL:   {COLOR_BOLD}{COLOR_FRONTEND}{url}{COLOR_RESET}
   📡  Tunneling Target:   http://localhost:{ngrok_port}
   
   👉  To connect to ChatGPT / Claude Custom MCP:
       Use: {COLOR_BOLD}{COLOR_API}{url}/mcp{COLOR_RESET} (if port 8000 is tunneled)
========================================================================
"""
            print(banner)
            break

def main():
    parser = argparse.ArgumentParser(description="Guardian Dev Runner (API, MCP, Frontend, Ngrok)")
    parser.add_argument("--ngrok-port", type=int, default=8000, help="Port to tunnel with ngrok (default: 8000 for MCP)")
    parser.add_argument("--ngrok-domain", type=str, default=os.getenv("NGROK_DOMAIN"), help="Custom/static ngrok domain (e.g. your-subdomain.ngrok-free.app)")
    parser.add_argument("--no-frontend", action="store_true", help="Do not run the frontend React server")
    parser.add_argument("--no-mcp", action="store_true", help="Do not run the MCP server")
    parser.add_argument("--no-api", action="store_true", help="Do not run the REST API")
    parser.add_argument("--no-ngrok", action="store_true", help="Do not run ngrok")
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = get_python_executable()
    print_log("System", f"Using Python executable: {python_path}", COLOR_BOLD)

    # 1. Port checks
    port_errors = False
    if not args.no_mcp and check_port(8000):
        print_log("System", "Port 8000 (MCP Server) is already in use!", COLOR_SYSTEM)
        port_errors = True
    if not args.no_api and check_port(8001):
        print_log("System", "Port 8001 (Dashboard REST API) is already in use!", COLOR_SYSTEM)
        port_errors = True
    if not args.no_frontend and check_port(5173):
        print_log("System", "Port 5173 (Frontend Dev) is already in use!", COLOR_SYSTEM)
        port_errors = True
    
    if port_errors:
        print_log("System", "Please close conflicting processes before running this script.", COLOR_SYSTEM)
        sys.exit(1)

    processes = {}
    threads = []
    stop_event = threading.Event()

    # Load ai-security-gateway/env if it exists
    env = os.environ.copy()
    env["AUTH_ENABLED"] = "false"
    gateway_env = os.path.join(root_dir, "ai-security-gateway", ".env")
    if os.path.exists(gateway_env):
        with open(gateway_env, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in env:
                        env[k] = v

    # Add project root to python path for backend processes
    env["PYTHONPATH"] = os.path.join(root_dir, "ai-security-gateway")

    try:
        # Start Backend API
        if not args.no_api:
            print_log("System", "Starting Backend REST API on port 8001...", COLOR_BOLD)
            api_cmd = [python_path, "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1", "--port", "8001"]
            proc = subprocess.Popen(
                api_cmd,
                cwd=os.path.join(root_dir, "ai-security-gateway"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            processes["Backend API"] = proc
            t = threading.Thread(target=stream_output, args=(proc, "Backend API", COLOR_API), daemon=True)
            t.start()
            threads.append(t)

        # Start MCP Server
        if not args.no_mcp:
            print_log("System", "Starting MCP Server on port 8000...", COLOR_BOLD)
            mcp_cmd = [python_path, "-m", "uvicorn", "mcp_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
            proc = subprocess.Popen(
                mcp_cmd,
                cwd=os.path.join(root_dir, "ai-security-gateway"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            processes["MCP Server"] = proc
            t = threading.Thread(target=stream_output, args=(proc, "MCP Server", COLOR_MCP), daemon=True)
            t.start()
            threads.append(t)

        # Start Frontend
        if not args.no_frontend:
            if shutil.which("npm") is None:
                print_log("System", "npm was not found. Frontend cannot be started automatically.", COLOR_SYSTEM)
            else:
                print_log("System", "Starting Frontend dev server on port 5173...", COLOR_BOLD)
                frontend_proc = subprocess.Popen(
                    ["npm", "run", "dev"],
                    cwd=os.path.join(root_dir, "frontend"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=True
                )
                processes["Frontend"] = frontend_proc
                t = threading.Thread(target=stream_output, args=(frontend_proc, "Frontend", COLOR_FRONTEND), daemon=True)
                t.start()
                threads.append(t)

        # Start Ngrok
        if not args.no_ngrok:
            if shutil.which("ngrok") is None:
                print_log("System", "ngrok was not found in PATH. Exiting ngrok integration.", COLOR_SYSTEM)
            else:
                ngrok_cmd = ["ngrok", "http", str(args.ngrok_port)]
                if args.ngrok_domain:
                    ngrok_cmd.append(f"--domain={args.ngrok_domain}")
                    print_log("System", f"Using static ngrok domain: {args.ngrok_domain}", COLOR_NGROK)
                ngrok_proc = subprocess.Popen(
                    ngrok_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=True
                )
                processes["Ngrok"] = ngrok_proc
                t = threading.Thread(target=stream_output, args=(ngrok_proc, "Ngrok", COLOR_NGROK), daemon=True)
                t.start()
                threads.append(t)

                # Monitor ngrok in a separate thread
                monitor_thread = threading.Thread(target=monitor_ngrok, args=(args.ngrok_port, stop_event), daemon=True)
                monitor_thread.start()

        # Keep main thread alive and monitor processes
        while True:
            # Check if any process has exited unexpectedly
            for name, proc in list(processes.items()):
                exit_code = proc.poll()
                if exit_code is not None:
                    print_log("System", f"{name} exited unexpectedly with code {exit_code}.", COLOR_SYSTEM)
                    # Remove from active monitoring so we don't log repeatedly
                    del processes[name]
            
            # If all components are stopped, break
            if not processes:
                print_log("System", "No active processes running.", COLOR_BOLD)
                break
                
            time.sleep(1)

    except KeyboardInterrupt:
        print_log("System", "Ctrl+C received. Cleaning up...", COLOR_BOLD)
    finally:
        stop_event.set()
        
        # Shutdown all active subprocesses
        print("\nShutting down all services...")
        for name, proc in processes.items():
            if proc.poll() is None:
                print_log("System", f"Terminating {name} (PID {proc.pid})...", COLOR_BOLD)
                try:
                    proc.terminate()
                except Exception as e:
                    print_log("System", f"Error terminating {name}: {e}", COLOR_SYSTEM)
        
        # Allow processes a brief moment to exit cleanly
        time.sleep(1.5)
        
        # Force-kill remaining processes
        for name, proc in processes.items():
            if proc.poll() is None:
                print_log("System", f"Force-killing {name} (PID {proc.pid})...", COLOR_BOLD)
                try:
                    proc.kill()
                except Exception as e:
                    print_log("System", f"Error killing {name}: {e}", COLOR_SYSTEM)

if __name__ == "__main__":
    main()
