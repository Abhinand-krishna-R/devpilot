# sample_project — intentionally vulnerable

**Do not copy anything from this directory into a real project, and do not
"fix" it.**

This is a deliberately bad Python project used to demo and manually test
DevPilot. It contains, on purpose:

- `pkg/utils.py` — a hardcoded password (`hardcoded_secret_123`), shell
  injection via `os.system` and `subprocess.call(..., shell=True)`, and a
  deeply nested function that trips the complexity and argument-count checks.
- `pkg/models.py` — a module that depends on `pkg.utils`, so the architecture
  analyzer has a real coupling edge to report.

Every finding here is bait for the analyzers. The credential is fake and is
not a real secret.

Run DevPilot against it to see a full report:

```bash
devpilot full sample_project --no-llm
python -m devpilot full sample_project --no-llm   # if PATH doesn't have devpilot
```

Bandit and other security scanners will (correctly) flag the contents of this
directory. It is excluded from the project's own CI dogfooding run, which
targets `devpilot/` only.
