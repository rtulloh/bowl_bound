# Python, pip and environment setup

[Player guide](README.md) · [Installation](installation.md) · [Optional chart import](importing-teams.md)

**Standalone players do not need Python, pip or Node.js.** Python is needed
only for running from source or using the separate PDF chart extractor. The
core/source tools require Python 3.10+; Python 3.12 is the tested local baseline.
Use a supported Python security release and avoid changing your system Python.

## Windows

- Download from [Python for Windows](https://www.python.org/downloads/windows/).
- Follow the official [Windows setup instructions](https://docs.python.org/3/using/windows.html).
  Installer/install-manager options vary; install Python for your user account
  and ensure the Python launcher/command is available. Reopen PowerShell afterward.
- Verify `py -3 --version` shows 3.10 or newer. If `py` is unavailable but
  `python --version` identifies your installed Python, substitute `python` for
  `py -3` in environment-creation commands. Avoid a Store shortcut that opens
  an installer rather than running the interpreter.

From the Bowl Bound source checkout, create a project environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip install -e ".[pdf]"
```

Use `.[web]` instead for source web play, or `.[web,pdf]` for both. Explicit
interpreter paths mean activation and PowerShell execution-policy changes are
unnecessary. If multiple Python versions are installed, select a supported one
explicitly, for example `py -3.12 -m venv .venv`.

## macOS with Homebrew

- Install Homebrew using its official instructions at [brew.sh](https://brew.sh/).
  Review the instructions and complete its PATH setup for your machine.
- [Homebrew Python guidance](https://docs.brew.sh/Homebrew-and-Python) explains
  versioned commands, virtual environments and managed package restrictions.

Install the tested Python line and verify it:

```sh
brew install python@3.12
python3.12 --version
python3.12 -m venv .venv
.venv/bin/python -m pip --version
.venv/bin/python -m pip install -e ".[pdf]"
```

Run the environment-creation/install commands from the Bowl Bound source root.
Use `python3.12` instead of `python3` in later setup examples if your unversioned
command selects an older/different Python. The environment's own Python command
is always `.venv/bin/python`. If the versioned command is not on PATH, follow
Homebrew's printed caveats or use `"$(brew --prefix python@3.12)/bin/python3.12"`.
Do not replace Apple's system Python, use sudo pip, or bypass an
externally-managed-environment warning with a system-wide package override.

Alternatively use the official [macOS Python installer](https://www.python.org/downloads/macos/)
and [macOS instructions](https://docs.python.org/3/using/mac.html).

## Linux

Use your distribution's supported Python 3.10+ packages, including its venv/pip
packages if those are separate. Follow the distribution's documentation rather
than replacing its system interpreter. Then, from the source root:

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip --version
.venv/bin/python -m pip install -e ".[pdf]"
```

## pip help

pip normally comes with a newly created virtual environment. Always use
`ENVIRONMENT_PYTHON -m pip` so packages go into the interpreter you actually run.
See the official [pip installation guide](https://pip.pypa.io/en/stable/installation/)
and [virtual-environment tutorial](https://docs.python.org/3/tutorial/venv.html).

If pip is missing from an otherwise valid environment, use that environment's
Python with `-m ensurepip --upgrade`, then `-m pip --version`. On distributions
that disable ensurepip, install the distribution's venv/pip package and recreate
a new environment instead. Do not download arbitrary pip bootstrap scripts or
install Bowl Bound packages into a protected global interpreter.

After setup, return to [extracting/importing charts](importing-teams.md) or the
[source web installation steps](installation.md#run-from-source). Node is needed
only for frontend source builds, not for PDF extraction or terminal play.
