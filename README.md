# DevPilot — AI Developer Assistant

DevPilot analyzes a codebase using real static-analysis tools (Bandit, Radon,
AST) and then asks Claude to turn the raw findings into a short, prioritized,
human-readable report. It's exposed two ways:

- **CLI** — run it directly from your terminal on any project.
- **MCP server** — plug it into Claude Desktop or Claude Code so Claude can
  call these skills as tools during a conversation.

## Skills

| Skill | What it does | Under the hood |
|---|---|---|
| `review_code` | Full-codebase code review | Radon cyclomatic complexity + maintainability index, plus AST checks for long functions, too many args, missing docstrings |
| `security_audit` | Security scan | Bandit (industry-standard Python SAST tool) |
| `architecture_analysis` | Structural overview | Custom AST-based import graph: module coupling (fan-in/fan-out), circular imports, largest files |
| `full_analysis` | Runs all three and combines the results | — |

Each skill returns the raw findings (JSON) *and*, if `ANTHROPIC_API_KEY` is
set, an LLM-generated summary that prioritizes the issues and suggests fixes.
Without an API key, you still get full raw findings — the LLM step is purely
additive.

## Install

### Recommended: pipx (CLI users)

[pipx](https://pipx.pypa.io) installs DevPilot into its own isolated environment
and puts the `devpilot` command on your PATH.

```bash
pipx install .          # from the project root
pipx ensurepath         # once; then open a NEW terminal
devpilot --help
```

Use `pipx install -e .` if you're editing the source and want changes to take
effect immediately. An editable install is linked to the project folder, so
moving or deleting the folder breaks the `devpilot` command until you reinstall.

To enable AI summaries, set your API key (optional):

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # macOS / Linux
```
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."        # Windows PowerShell (this session)
```
```bat
set ANTHROPIC_API_KEY=sk-ant-...             :: Windows cmd (this session)
```

Without a key, everything still works and you get the raw findings.

### Contributors: virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```
If activation is blocked, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Windows (cmd):**
```bat
python -m venv venv
venv\Scripts\activate.bat
pip install -e ".[dev]"
```

Avoid installing into a global or shared Python. DevPilot's `mcp` dependency
requires `starlette>=1.0`, which conflicts with older FastAPI releases
(FastAPI 0.110 pins `starlette<0.38`) and can break FastAPI apps in the same
environment. pipx or a venv avoids this.

## CLI usage

Two equivalent ways to run every command — use whichever works on your system:

```bash
devpilot review /path/to/project          # via the installed console script
python -m devpilot review /path/to/project   # always works, no PATH needed
```

```bash
devpilot review /path/to/project
devpilot security /path/to/project
devpilot architecture /path/to/project
devpilot full /path/to/project

# Skip the AI summary and just see raw findings:
devpilot review /path/to/project --no-llm

# Machine-readable output:
devpilot security /path/to/project --json
```

`python -m devpilot ...` always works regardless of how DevPilot was
installed or what your PATH looks like — useful as a fallback if the
`devpilot` command itself isn't found (see Troubleshooting).

## MCP server usage

Run it directly for local stdio use (it waits for a client, so it looks like it hangs):

```bash
python -m devpilot.mcp_server
```

To use it from Claude Desktop, add a server entry to your MCP config
(`claude_desktop_config.json`). The `command` must point at the Python
interpreter that has DevPilot installed.

**If you installed with pipx**, find the venv location:

```bash
pipx environment      # look for PIPX_LOCAL_VENVS
```

Then use `<PIPX_LOCAL_VENVS>/devpilot/...` as the interpreter:

**Windows:**
```json
{
  "mcpServers": {
    "devpilot": {
      "command": "C:\\Users\\<you>\\AppData\\Local\\pipx\\pipx\\venvs\\devpilot\\Scripts\\python.exe",
      "args": ["-m", "devpilot.mcp_server"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

**macOS / Linux:**
```json
{
  "mcpServers": {
    "devpilot": {
      "command": "/path/from/PIPX_LOCAL_VENVS/devpilot/bin/python",
      "args": ["-m", "devpilot.mcp_server"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

**If you installed in a venv**, use that venv's interpreter instead
(`venv/bin/python` on macOS/Linux, `venv\Scripts\python.exe` on Windows,
as an absolute path).

JSON needs doubled backslashes on Windows. Fully quit and restart Claude
Desktop after editing the config. Then try: *"Run a security audit on
C:\code\my-app using DevPilot."* The `ANTHROPIC_API_KEY` entry is optional.

## Project structure

```
devpilot/
  devpilot/
    analyzers/
      security.py        # Bandit wrapper + severity summarization
      code_review.py      # Radon complexity/maintainability + AST style checks
      architecture.py      # Import graph, coupling, circular import detection
    utils/
      llm_summary.py      # Sends findings to Claude, gets prioritized summary
    core.py               # Orchestrates analyzers -> shared by CLI and MCP
    cli.py                # Click-based CLI
    mcp_server.py         # MCP server exposing the same skills as tools
    validation.py         # Shared project-path validation for CLI and MCP
    __main__.py           # Enables `python -m devpilot`
  tests/                  # pytest suite (analyzers, CLI, MCP, path validation)
  sample_project/         # Deliberately vulnerable demo — see its own README
  .github/workflows/ci.yml
  pyproject.toml          # Packaging, dependency pins, ruff + pytest config
  requirements.txt        # Mirrors the runtime pins in pyproject.toml
  LICENSE
```

## Troubleshooting

**`'devpilot' is not recognized` (Windows)**
1. Run `pipx ensurepath` (or `python -m pipx ensurepath` if `pipx` itself isn't found).
2. Close all terminals and fully quit your IDE. Terminals embedded in VS Code
   and similar tools keep the old PATH until the whole app restarts.
3. In a new window, run `Get-Command devpilot`. For a pipx install it should
   point at `C:\Users\<you>\.local\bin\devpilot.exe`.

To refresh a stale PowerShell session without restarting it:
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
```

`python -m devpilot ...` works regardless of PATH as long as DevPilot is
installed in the Python you're calling.

**`devpilot` runs an old copy, or two `devpilot.exe` files exist**
A global `pip install` and a pipx install can both provide `devpilot.exe`.
`pip show devpilot` should say "Package(s) not found" if you use pipx. If it
lists a package, run `pip uninstall devpilot` and reopen the terminal.

**`ModuleNotFoundError: No module named 'radon'` (or bandit/mcp/anthropic/click)**
Dependencies aren't installed in the Python you're running. With pipx,
reinstall (`pipx install --force .`). With a venv, activate it and run
`pip install -e .`. Check with `pip show radon`.

**pip warns about a `starlette`/`fastapi` conflict**
See the note under Install. Give DevPilot its own environment with pipx or a
venv. If `mcp` already upgraded starlette in a shared environment, repair it by
uninstalling DevPilot's global copy and `mcp`, then reinstalling the version
your other app needs (for example `pip install "starlette>=0.37.2,<0.38"` for
FastAPI 0.110). `pip check` should then come back clean.

## Testing

DevPilot has a real pytest suite covering each analyzer against a clean
project, a deliberately vulnerable/messy project, a project with a Python
syntax error, and an empty project — plus CLI smoke tests, path validation
tests, and MCP server tests (including the bad-path error-handling
behavior). Run `pytest tests/ -v` for the current count; it's grown as the
project has, so don't trust a specific number in prose.

Testing requires the contributor setup (the venv install under
"Contributors: virtual environment" above, with `pip install -e ".[dev]"`),
since pipx installs don't include dev dependencies or expose the source
tree for editing:

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

CI (`.github/workflows/ci.yml`) runs this suite on Python 3.10–3.12 on Linux
plus Python 3.12 on Windows, on every push and PR. It also lints and checks
formatting with ruff, and dogfoods DevPilot by running its own code-review
skill against its own source as a smoke test.

## Testing DevPilot on itself (dogfooding)

Because it's a static-analysis tool, the most honest test of DevPilot is
running it on its own source (from a contributor venv install):

```bash
devpilot full devpilot --no-llm --json
```

This is genuinely useful during development — it's how several real bugs
were caught and fixed while building this (a silent exception swallow in the
maintainability check, a false-positive-prone subprocess call needing a
justified `# nosec`, missing docstrings, and — the most substantial one — an
architecture-analysis bug where imports like `import pkg.b` were resolved
only to the top-level `pkg` package instead of the specific submodule,
which silently hid real circular imports and coupling).

## Known limitations

- **Python only.** The AST-based analyzers (code review, architecture) only
  understand Python. Bandit is also Python-specific. Extending to other
  languages would mean swapping in language-specific tools (e.g. Semgrep
  works multi-language and could replace/augment Bandit).
- **No LLM without an API key.** The AI-summary step is optional — without
  it, DevPilot is a static-analysis aggregator with structured JSON output.
- **Bandit only flags what its rule set covers** (common patterns like shell
  injection, hardcoded secrets, weak crypto). It won't catch business-logic
  vulnerabilities.
- **Circular-import detection is DFS-based and caps at 10 reported cycles.**
  Correct for typical project sizes, but on a very large, densely
  interconnected codebase the search could in principle be slow; there's no
  hard iteration limit, which would be worth adding before pointing this at
  a huge monorepo.

## Possible next steps

- Add Semgrep for multi-language security/style rules.
- Add a "Figma-to-code" skill as a fourth tool.
- Cache analysis results per-commit so re-running on an unchanged file is instant.
- Add a `--diff` mode that only analyzes files changed in the current git branch.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Contributions are welcome. Before opening a pull request:

1. Install the dev dependencies into a virtual environment:
   `pip install -e ".[dev]"`
2. Run exactly the checks CI runs, and make sure all three pass:

   ```bash
   ruff check devpilot/ tests/
   ruff format --check devpilot/ tests/
   pytest tests/ -v
   ```

3. Keep the analyzers dependency-light. DevPilot deliberately builds on
   standard, well-known tools (Bandit, Radon) rather than a large framework,
   so a new runtime dependency needs a strong justification.
4. If you change what an analyzer returns, update the tests under `tests/` —
   the suite doubles as the specification for the JSON shape each skill
   returns.

CI must be green on Python 3.10–3.12 (Linux) and 3.12 (Windows) before a pull
request can be merged.
