#!/bin/bash
echo "============================================"
echo "  CodeAgent Installer"
echo "  Offline Coding Agent powered by Local LLMs"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Install with: sudo apt install python3 python3-pip"
    exit 1
fi
echo "[OK] Python found: $(python3 --version)"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "[WARNING] Ollama is not installed."
    echo "Install with: curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    read -p "Continue anyway? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "[OK] Ollama found: $(ollama --version)"
fi

# Install CodeAgent
echo ""
echo "Installing CodeAgent..."
pip3 install -e . 2>/dev/null || python3 -m pip install -e .

echo ""
echo "[OK] CodeAgent installed!"
echo ""

# Pull the coding model
echo "Checking for coding LLM model..."
if ! ollama list 2>/dev/null | grep -qi "qwen2.5-coder"; then
    echo ""
    echo "Downloading qwen2.5-coder:7b-instruct model..."
    ollama pull qwen2.5-coder:7b-instruct-q4_K_M
else
    echo "[OK] Coding model already available"
fi

echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "To start CodeAgent:"
echo "  codeagent"
echo ""
echo "Or with a specific directory:"
echo "  codeagent --dir /your/project"
echo ""
echo "For fully offline mode:"
echo "  codeagent --no-web"
echo ""
echo "Type /help inside CodeAgent for all commands."
