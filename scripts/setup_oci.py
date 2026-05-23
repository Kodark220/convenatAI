#!/usr/bin/env python3
"""
Set up convenatAI on OCI — run this once SSH is available.
Sets up API backend + 24/7 agent worker as systemd services.
Usage: python3 setup_oci.py
"""
import subprocess, sys, os

HOST = "ubuntu@79.76.62.48"
KEY = os.path.expanduser("~/.ssh/oci-79.76.62.48.key")

def run(cmd):
    print(f"  $ {cmd}")
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", "-i", KEY, HOST, cmd],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        print(f"  FAILED: {r.stderr[:300]}")
        return False
    print(f"  OK")
    return True

def write_remote(path, content):
    """Write content to a remote file using SSH stdin."""
    proc = subprocess.Popen(
        ["ssh", "-o", "ConnectTimeout=15", "-i", KEY, HOST,
         f"sudo tee {path} > /dev/null"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=content, timeout=15)
    if proc.returncode != 0:
        print(f"  FAILED writing {path}: {stderr[:200]}")
        return False
    print(f"  Wrote {path}")
    return True

print("=== Setting up convenatAI Backend + Worker Services ===\n")

# 1. Install missing deps
print("1. Installing Python deps...")
run("cd /home/ubuntu/convenatAI && pip3 install --user -e . 2>&1 | tail -3")

# 2. Copy service files
print("\n2. Installing systemd services...")

API_SVC = """[Unit]
Description=convenatAI Backend API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/convenatAI
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin:/bin
EnvironmentFile=/home/ubuntu/convenatAI/.env
ExecStart=/usr/bin/python3 /home/ubuntu/convenatAI/serve.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

WORKER_SVC = """[Unit]
Description=convenatAI Agent Worker (24/7)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/convenatAI
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin:/bin
EnvironmentFile=/home/ubuntu/convenatAI/.env
ExecStart=/usr/bin/python3 /home/ubuntu/convenatAI/worker.py --interval 120 --live
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

if not write_remote("/etc/systemd/system/convenatAI.service", API_SVC):
    sys.exit(1)
if not write_remote("/etc/systemd/system/convenatAI-worker.service", WORKER_SVC):
    sys.exit(1)

run("sudo systemctl daemon-reload")
run("sudo systemctl enable convenatAPI")
run("sudo systemctl enable convenatAI-worker")

# 3. Start the services
print("\n3. Starting services...")
run("sudo systemctl start convenatAI")
run("sudo systemctl start convenatAI-worker")

# 4. Verify
print("\n4. Verifying...")
run("sleep 3 && sudo systemctl status convenatAI --no-pager | grep 'Active:'")
run("sudo systemctl status convenatAI-worker --no-pager | grep 'Active:'")
run("curl -s http://localhost:8001/api/stats 2>/dev/null | head -5 || echo 'API starting...'")
run("journalctl -u convenatAI-worker --no-pager -n 10 2>/dev/null | head -10 || echo 'Worker starting...'")

print("\n=== convenatAI is now running 24/7 on OCI ===")
print("  API:     http://79.76.62.48:8001")
print("  Worker:  systemctl status convenatAI-worker")
print("  Logs:    journalctl -u convenatAI-worker -f")
