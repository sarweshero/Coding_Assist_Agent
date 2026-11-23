#!/bin/bash
# Conding-Assist setup script
# - creates virtualenv + installs backend dependencies
# - prepares data directory
# - installs + starts the FastAPI server via systemd
# - ensures the 'sarassist' shell alias exists and reloads bash config

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

cd "$BACKEND_DIR"

echo "==> Setting up Conding-Assist backend..."

if [ ! -d ".venv" ]; then
    echo "==> Creating virtualenv..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Preparing data directory..."
mkdir -p data

echo "==> Installing and starting Conding-Assist systemd service..."
sudo tee /etc/systemd/system/conding-assist.service > /dev/null <<EOF
[Unit]
Description=Conding-Assist Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$BACKEND_DIR/.venv/bin
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now conding-assist
sudo systemctl status conding-assist --no-pager

echo "==> Ensuring 'sarassist' alias exists..."

SARASSIST_BLOCK='sarassist() {
    if [ "$#" -eq 0 ]; then
        echo "sarassist - Conding-Assist autonomous software engineering assistant"
        echo ""
        echo "Interactive assistant is started with: python -m app.cli"
        echo "Full command list:"
        echo "  new <name>              Create a new project"
        echo "  requirements <text>    Update client requirements"
        echo "  plan                    Orchestrator plans modules from requirements"
        echo "  approve                 Approve requirements -> start IMPLEMENTING_MODULE"
        echo "  run <index>             Run developer + QA agent loop for module at index"
        echo "  review <index>          Run code review on module at index"
        echo "  review history <i>     Show review history for module at index"
        echo "  status                  Show project / module / test status"
        echo "  mode <PLAN|EDIT|FIX|EXPLAIN>  Switch operating mode"
        echo "  config                  Open interactive config wizard"
        echo "  help                    Show this help"
        echo "  quit                    Exit"
        return 0
    fi
    local backend_dir=/home/sarwesh/Projects/Conding-Assist/backend
    cd "$backend_dir"
    "$backend_dir/.venv/bin/python" -m app.cli "$@"
}'

if ! grep -q "^sarassist()" ~/.bashrc; then
    printf '\n%s\n' "$SARASSIST_BLOCK" >> ~/.bashrc
    echo "sarassist alias added to ~/.bashrc"
else
    echo "sarassist alias already exists in ~/.bashrc"
fi

echo "==> Refreshing bash configuration..."
source ~/.bashrc

echo ""
echo "==> Conding-Assist setup complete."
echo "    Service: systemctl status conding-assist"
echo "    Logs:    journalctl -u conding-assist -f"
echo "    CLI:     sarassist   (or 'python -m app.cli' from backend/)"
