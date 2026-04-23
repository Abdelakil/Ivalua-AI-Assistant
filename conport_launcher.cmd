@echo off
REM ============================================================================
REM Portable ConPort launcher (Windows) - plug & play, no admin rights.
REM
REM On first run:
REM   1) Downloads a standalone `uv` binary (~20MB) into .tools\ (no installer).
REM   2) `uv` auto-downloads a portable CPython into the user cache on first use.
REM   3) `uv run` builds a project-local .venv from pyproject.toml and installs
REM      context-portal-mcp + deps (no admin rights needed).
REM   4) Launches the safety proxy, which spawns conport-mcp as a child.
REM
REM On subsequent runs: everything is cached, startup is near-instant.
REM
REM This script is what your MCP client (Windsurf) should point to.
REM Example mcp_config.json entry:
REM   {
REM     "conport": {
REM       "command": "C:\\path\\to\\project\\conport_launcher.cmd",
REM       "disabled": false
REM     }
REM   }
REM ============================================================================
setlocal enabledelayedexpansion

REM Resolve project root (directory containing this .cmd)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "TOOLS=%ROOT%\.tools"
set "UV_BIN=%TOOLS%\uv.exe"
set "PROXY=%ROOT%\context_portal\scripts\conport_safe_proxy.py"

REM ---- Locate uv: project-local, then system PATH, then download ------------
if not exist "%UV_BIN%" (
    for /f "delims=" %%U in ('where uv.exe 2^>nul') do (
        if not defined UV_SYS set "UV_SYS=%%U"
    )
    if defined UV_SYS (
        set "UV_BIN=!UV_SYS!"
        1>&2 echo [conport_launcher] using system uv: !UV_BIN!
    ) else (
        1>&2 echo [conport_launcher] First run: downloading portable uv...
        if not exist "%TOOLS%" mkdir "%TOOLS%"
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue';" ^
            "$url = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip';" ^
            "$zip = Join-Path '%TOOLS%' 'uv.zip';" ^
            "Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
            "Expand-Archive -Path $zip -DestinationPath '%TOOLS%' -Force;" ^
            "Remove-Item $zip -Force" 1>&2
        if errorlevel 1 (
            1>&2 echo [conport_launcher] ERROR: failed to download uv and no system uv found.
            exit /b 1
        )
        if not exist "%UV_BIN%" (
            1>&2 echo [conport_launcher] ERROR: uv.exe not found after extraction.
            exit /b 1
        )
        1>&2 echo [conport_launcher] uv ready at %UV_BIN%
    )
)

REM Tell the proxy to use our bundled uv instead of system `uvx`
set "UV_BIN=%UV_BIN%"

REM Keep uv/Python/pip caches project-local (fully self-contained folder)
set "UV_CACHE_DIR=%TOOLS%\uv-cache"
set "UV_PYTHON_INSTALL_DIR=%TOOLS%\python"

REM ---- Run the proxy via uv (handles venv + deps automatically) --------------
REM `uv run` reads pyproject.toml, ensures .venv is synced, then execs the script.
"%UV_BIN%" run --project "%ROOT%" python "%PROXY%"
exit /b %ERRORLEVEL%
