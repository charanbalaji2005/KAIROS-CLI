<p align="center">
  <img src="assets/mascot.gif" alt="Kairos Mascot" width="220" />
</p>

# ⟦>_⟧ KAIROS AGENT

**Autonomous Terminal Engineer (Claude-Code Architecture in Python)**

Kairos is an AI-powered terminal coding agent — capable of understanding repositories, editing code with precision, running tests, committing, and pushing to GitHub autonomously.

```
      ⟦>_⟧  KAIROS AGENT v0.2.0
            Autonomous Terminal Engineer

            Model: qwen/qwen3.8-27b (Groq LPUs)
            Workspace: ~/projects/my-app
            Branch: main
            GitHub: ● connected as charanbalaji2005

 ──────────────────────────────────────────────────────────

 kairos > build the authentication system and push to GitHub
```

---

## Features

- **Full terminal UI** — orange-on-black Kairos aesthetic, compact header with live mascot
- **Autonomous agent** — plans, reads, edits, tests, commits, pushes
- **Groq LPU Acceleration** — lightning fast inference with Qwen 27B, GPT-OSS 120B, Compound
- **Multi-model & Cloud support** — Groq, Ollama (local), Anthropic Claude, OpenAI, Gemini
- **GitHub CLI integration** — push, PR, CI status via `gh` (no token stored)
- **Slash commands** — `/help /clear /git /github /diff /model /doctor /exit`
- **Approval dialogs** — dangerous ops require `[y]/[n]` confirmation
- **Auto mode** — skip confirmations for fully autonomous workflows
- **History navigation** — ↑/↓ arrows through command history
- **Tab autocomplete** — slash command picker

---

## Quick Start

### Prerequisites

```bash
# Python 3.10+
python --version

# (Optional) Install GitHub CLI for PRs and CI checks
gh auth login
```

### Installation

```bash
git clone https://github.com/charanbalaji2005/KAIROS-CLI.git
cd KAIROS-CLI
pip install -r requirements.txt
pip install -e .
```

### Start Kairos

```bash
# Direct launcher command
kairos

# Or via Python script
python kairos.py

# (Alias 'forge' also supported)
forge
```

---

## Models

Kairos supports lightning-fast cloud inference via Groq LPUs, local models via Ollama, and frontier cloud providers:

| Model | Provider | Best For | Speed |
|-------|----------|----------|-------|
| `qwen/qwen3.8-27b` | Groq *(Default)* | Code generation, reasoning | Ultra Fast (LPUs) |
| `openai/gpt-oss-120b` | Groq | Deep architectural reasoning | Very Fast |
| `groq/compound` | Groq | Multi-step agentic workflows | Ultra Fast |
| `llama-3.3-70b-versatile` | Groq | General coding & refactoring | Ultra Fast |
| `qwen-coder` | Ollama (Local) | Local private coding | Local hardware |
| `claude-3-5-sonnet` | Anthropic | Frontier code synthesis | Cloud API |
| `gpt-4o` | OpenAI | Frontier reasoning | Cloud API |

```bash
# Switch models
kairos model set qwen/qwen3.8-27b
kairos model set openai/gpt-oss-120b

# List available models
kairos model list
```

---

## Commands

| Command | Action |
|---------|--------|
| `kairos` | Start interactive session |
| `kairos doctor` | Check environment, API keys, Git & GitHub CLI |
| `kairos model list` | List available models |
| `kairos model set <name>` | Set active LLM model |
| `kairos status` | Show current status |
| `kairos config` | View configuration |
| `kairos config <key> <val>` | Set config value |
| `kairos version` | Print version |

### In-session slash commands

```
/help         Show all commands
/clear        Clear conversation history
/git          Git status summary
/github       GitHub connection status
/diff         Show uncommitted diff
/model        Current/available models
/doctor       Environment check
/compact      Toggle compact header
/auto         Toggle autonomous confirmation mode
/sessions     List previous sessions
/exit         Exit Kairos
```

---

## Usage Examples

```
kairos > build a REST API for user authentication with JWT

kairos > add tests for the auth module and run them

kairos > commit these changes with a descriptive message and push

kairos > create a pull request with the changes

kairos > what's the current CI status?

kairos > read src/auth/login.py and optimize the database query
```

---

## Configuration

Config is stored at `~/.kairos/config.json`:

```json
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
```

Set via CLI:

```bash
kairos config model qwen/qwen3.8-27b
kairos config provider groq
kairos config auto_mode true
```

Set API keys:

```bash
kairos config groq_api_key gsk_...
kairos config anthropic_api_key sk-ant-...
kairos config openai_api_key sk-...
```

---

## Architecture

Kairos follows a modular Claude-Code architecture built in Python:

```text
kairos/
├── kairos.py                  # Direct CLI entry point
├── forge.py                   # Backward-compatible CLI entry point
├── install.sh                 # Single-line curl installer
├── pyproject.toml             # Package metadata & script entry points
│
├── forge/
│   ├── cli.py                 # Typer subcommands (doctor, status, model, config)
│   ├── agent/
│   │   ├── runtime.py         # Autonomous agent execution loop
│   │   ├── context.py         # Dynamic system prompt & repo intelligence
│   │   ├── planner.py         # Task planning & step tracking
│   │   ├── memory.py          # Session memory & scratchpad
│   │   ├── compaction.py      # Context window compression
│   │   └── state.py           # Event and state types
│   ├── llm/
│   │   ├── groq.py            # Groq LPU provider
│   │   ├── anthropic.py       # Anthropic Claude provider
│   │   ├── openai.py          # OpenAI GPT provider
│   │   ├── ollama.py          # Ollama local provider
│   │   └── gemini.py          # Google Gemini provider
│   ├── terminal/
│   │   ├── ui.py              # Interactive prompt-toolkit terminal shell
│   │   ├── renderer.py        # Rich styling, orange theme & ASCII mascot
│   │   └── streaming.py       # Live spinner & output streaming
│   ├── tools/
│   │   ├── filesystem.py      # Safe read/edit/write tools
│   │   ├── shell.py           # Sandboxed command execution
│   │   ├── git.py             # Git status, diff, commit, push
│   │   ├── github.py          # GitHub CLI client (PR, CI)
│   │   └── search.py          # Ripgrep & file pattern search
│   ├── permissions/
│   │   ├── policy.py          # Danger rating & approval policies
│   │   └── manager.py         # Interactive prompt / auto-mode manager
│   ├── repository/
│   │   └── detector.py        # Framework, language & test-runner detector
│   ├── sessions/
│   │   └── storage.py         # Session persistence & resume
│   └── config/
│       ├── schema.py          # Pydantic configuration schema
│       └── loader.py          # Config loader & env var parser
```

---

## Permission Model

| Operation | Requires Approval | Auto Mode |
|-----------|-------------------|-----------|
| Read files | Never | Auto |
| Edit files | Never | Auto |
| Shell exec | Never | Auto |
| Git commit | Never | Auto |
| **git push** | **Yes** | Auto |
| **GitHub PR** | **Yes** | Auto |
| **Delete files** | **Yes** | Auto |

Enable auto mode: `kairos --auto` or `kairos config auto_mode true`

---

## One-Line Installer

### Linux & WSL

```bash
curl -fsSL https://raw.githubusercontent.com/charanbalaji2005/KAIROS-CLI/main/install.sh | bash
```

---

## License

MIT — Kairos Agent by Charan Balaji
