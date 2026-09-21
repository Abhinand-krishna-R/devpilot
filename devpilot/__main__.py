"""
Allows running the CLI as `python -m devpilot ...` in addition to the
`devpilot` console script. This matters on Windows, where the console
script's location (venv\\Scripts or a user site-packages Scripts folder)
is often not on PATH — `python -m devpilot` always works because it only
depends on Python itself being callable, not on PATH containing the
scripts directory.
"""

from devpilot.cli import main

if __name__ == "__main__":
    main()
