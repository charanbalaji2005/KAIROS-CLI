#!/usr/bin/env bash
# Kairos Agent Installer (Python)
# Usage: bash install.sh or curl -fsSL https://raw.githubusercontent.com/charanbalaji2005/KAIROS-CLI/main/install.sh | bash

set -euo pipefail

KAIROS_VERSION="0.2.0"
KAIROS_HOME="${HOME}/.kairos"
INSTALL_DIR="${KAIROS_HOME}/bin"
VENV_DIR="${KAIROS_HOME}/venv"
APP_DIR="${KAIROS_HOME}/app"
BINARY_NAME="kairos"
ALT_BINARY="forge"

# Colors
ORANGE='\033[38;2;249;115;22m'
GREEN='\033[38;2;34;197;94m'
RED='\033[38;2;239;68;68m'
MUTED='\033[38;2;163;163;163m'
RESET='\033[0m'

banner() {
  echo -e ""
  echo -e "${ORANGE}  ⟦>_⟧  KAIROS AGENT${RESET}"
  echo -e "${MUTED}  Autonomous Terminal Engineer (Python Core)${RESET}"
  echo -e "${MUTED}  Installing v${KAIROS_VERSION}...${RESET}"
  echo -e ""
}

check_deps() {
  echo -e "${MUTED}Checking dependencies...${RESET}"

  # Check Python
  PYTHON_BIN=""
  if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
  elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
  fi

  if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10+ first.${RESET}"
    exit 1
  fi

  # Check Python version >= 3.10
  PY_OK=$("$PYTHON_BIN" -c 'import sys; print(int(sys.version_info >= (3, 10)))' 2>/dev/null || echo "0")
  if [ "$PY_OK" != "1" ]; then
    echo -e "${RED}✗ Python 3.10 or higher is required.$RESET"
    exit 1
  fi
  PY_VER=$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
  echo -e "${GREEN}✓${RESET} Python ${PY_VER}"

  # Check Git
  if ! command -v git &>/dev/null; then
    echo -e "${RED}✗ Git not found. Install git first.${RESET}"
    exit 1
  fi
  echo -e "${GREEN}✓${RESET} Git"

  # Optional GitHub CLI
  if command -v gh &>/dev/null; then
    echo -e "${GREEN}✓${RESET} GitHub CLI"
  else
    echo -e "${MUTED}◆ GitHub CLI not found — install with: brew install gh or apt install gh${RESET}"
  fi

  # Optional Ollama
  if command -v ollama &>/dev/null; then
    echo -e "${GREEN}✓${RESET} Ollama"
  else
    echo -e "${MUTED}◆ Ollama not found — local models unavailable${RESET}"
  fi
}

install_kairos() {
  echo -e ""
  echo -e "${MUTED}Setting up Kairos environment in ${KAIROS_HOME}...${RESET}"
  mkdir -p "$INSTALL_DIR"

  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # Create virtual environment if it doesn't exist
  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${MUTED}Creating virtual environment...${RESET}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  VENV_PIP="${VENV_DIR}/bin/pip"
  VENV_PYTHON="${VENV_DIR}/bin/python"

  # Ensure pip is up to date
  "$VENV_PIP" install --upgrade pip --quiet

  # Install Kairos
  if [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    echo -e "${MUTED}Installing from local source (${SCRIPT_DIR})...${RESET}"
    "$VENV_PIP" install -e "${SCRIPT_DIR}" --quiet
  else
    echo -e "${MUTED}Cloning Kairos repository...${RESET}"
    rm -rf "$APP_DIR"
    git clone --depth 1 https://github.com/charanbalaji2005/KAIROS-CLI.git "$APP_DIR" --quiet
    "$VENV_PIP" install -e "$APP_DIR" --quiet
  fi

  # Create launcher binary script for kairos
  cat > "${INSTALL_DIR}/${BINARY_NAME}" << EOF
#!/usr/bin/env bash
exec "${VENV_PYTHON}" -m forge "\$@"
EOF
  chmod +x "${INSTALL_DIR}/${BINARY_NAME}"

  # Create symlink for forge alias
  ln -sf "${INSTALL_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/${ALT_BINARY}"

  echo -e "${GREEN}✓${RESET} Kairos binary installed at ${INSTALL_DIR}/${BINARY_NAME}"
  echo -e "${GREEN}✓${RESET} Forge alias created at ${INSTALL_DIR}/${ALT_BINARY}"

  # Symlink to /usr/local/bin if writable
  if [ -w "/usr/local/bin" ]; then
    ln -sf "${INSTALL_DIR}/${BINARY_NAME}" "/usr/local/bin/${BINARY_NAME}"
    ln -sf "${INSTALL_DIR}/${BINARY_NAME}" "/usr/local/bin/${ALT_BINARY}"
    echo -e "${GREEN}✓${RESET} Linked kairos & forge to /usr/local/bin"
  fi

  # Add to PATH (prepend so it takes precedence over system packages)
  SHELL_RC=""
  if [ -f "${HOME}/.zshrc" ]; then
    SHELL_RC="${HOME}/.zshrc"
  elif [ -f "${HOME}/.bashrc" ]; then
    SHELL_RC="${HOME}/.bashrc"
  fi

  if [ -n "$SHELL_RC" ]; then
    # Clean up previous kairos/forge bin lines
    sed -i '/\.kairos\/bin/d' "$SHELL_RC"
    sed -i '/\.forge\/bin/d' "$SHELL_RC"
    echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "$SHELL_RC"
    echo -e "${GREEN}✓${RESET} Added to PATH in ${SHELL_RC}"
  fi
}

setup_config() {
  echo -e ""
  echo -e "${MUTED}Setting up configuration...${RESET}"
  mkdir -p "${KAIROS_HOME}"

  # If previous ~/.forge/config.json exists and ~/.kairos/config.json does not, copy it over
  if [ -f "${HOME}/.forge/config.json" ] && [ ! -f "${KAIROS_HOME}/config.json" ]; then
    cp "${HOME}/.forge/config.json" "${KAIROS_HOME}/config.json"
    echo -e "${GREEN}✓${RESET} Migrated existing config from ~/.forge/ to ~/.kairos/config.json"
  elif [ ! -f "${KAIROS_HOME}/config.json" ]; then
    cat > "${KAIROS_HOME}/config.json" << 'EOF'
{
  "model": "qwen/qwen3.8-27b",
  "provider": "groq",
  "auto_mode": false,
  "ollama_url": "http://localhost:11434",
  "max_tokens": 4096,
  "temperature": 0.1,
  "theme": "dark",
  "compact_mode": false,
  "max_iterations": 30
}
EOF
    echo -e "${GREEN}✓${RESET} Config created at ~/.kairos/config.json"
  fi
}

suggest_model() {
  echo -e ""
  echo -e "${MUTED}To start Kairos:${RESET}"
  echo -e "  ${ORANGE}kairos${RESET}"
  echo -e ""
  echo -e "${MUTED}Or run doctor check:${RESET}"
  echo -e "  ${ORANGE}kairos doctor${RESET}"
  echo -e ""
}

banner
check_deps
install_kairos
setup_config
suggest_model

echo -e "${GREEN}✓ Kairos installed successfully!${RESET}"
echo -e ""
