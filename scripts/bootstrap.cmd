@echo off
REM ============================================================================
REM One-shot bootstrap (Windows).
REM
REM Runs the full first-run install WITHOUT launching the MCP proxy, so that
REM by the time your editor connects, everything is already cached and the
REM MCP server starts in < 3 seconds (well under the editor's 60 s timeout).
REM
REM Does exactly what conport_launcher.cmd does on first run:
REM   1) download portable uv.exe into .tools\
REM   2) uv downloads portable CPython
REM   3) uv sync builds .venv and installs context-portal-mcp + deps
REM   4) verifies the ConPort server can be imported
REM
REM Typical runtime on a fresh machine: 2-5 minutes (network-bound).
REM Safe to re-run - it is idempotent.
REM ============================================================================
setlocal enabledelayedexpansion

REM Repo root = parent of scripts\
set "ROOT=%~dp0..\"
pushd "%ROOT%"
for %%I in ("%CD%") do set "ROOT=%%~fI"
popd

REM ---- Re-run ourselves with stdout+stderr teed to bootstrap.log, so that if
REM      the window closes or a tool crashes, the user can still share the log.
set "BOOTSTRAP_LOG=%ROOT%\bootstrap.log"
if "%~1"=="--logged" goto :main
REM cmd /c does the stderr merge (pure text), PowerShell only tees stdout.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Continue';" ^
    "cmd /c '\"%~f0\" --logged 2>&1' | Tee-Object -FilePath '%BOOTSTRAP_LOG%';" ^
    "exit $LASTEXITCODE"
set "RC=%ERRORLEVEL%"
echo.
echo [bootstrap] Full log written to: %BOOTSTRAP_LOG%
echo [bootstrap] Exit code: %RC%
pause
exit /b %RC%

:main
echo [bootstrap] Project root: %ROOT%

set "TOOLS=%ROOT%\.tools"
set "UV_BIN=%TOOLS%\uv.exe"

echo [bootstrap] Step 1/3 -- locate uv
REM Prefer an existing uv: project-local first, then system-wide on PATH.
REM Only download as a last resort -- useful on locked-down machines where
REM github.com is blocked but a corporate-provisioned uv is already installed.
if exist "%UV_BIN%" (
    echo [bootstrap]   using project-local uv: %UV_BIN%
) else (
    for /f "delims=" %%U in ('where uv.exe 2^>nul') do (
        if not defined UV_SYS set "UV_SYS=%%U"
    )
    if defined UV_SYS (
        set "UV_BIN=!UV_SYS!"
        echo [bootstrap]   using system uv: !UV_BIN!
    ) else (
        if not exist "%TOOLS%" mkdir "%TOOLS%"
        echo [bootstrap]   no uv found -- downloading portable copy...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue';" ^
            "$url = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip';" ^
            "$zip = Join-Path '%TOOLS%' 'uv.zip';" ^
            "Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
            "Expand-Archive -Path $zip -DestinationPath '%TOOLS%' -Force;" ^
            "Remove-Item $zip -Force"
        if errorlevel 1 (
            echo [bootstrap] ERROR: failed to download uv and no system uv found.
            echo [bootstrap]        See https://github.com/astral-sh/uv or place uv.exe at %UV_BIN%
            pause
            exit /b 1
        )
        set "UV_BIN=%TOOLS%\uv.exe"
        if not exist "!UV_BIN!" (
            echo [bootstrap] ERROR: uv.exe not found after extraction.
            pause
            exit /b 1
        )
    )
)
"%UV_BIN%" --version

set "UV_CACHE_DIR=%TOOLS%\uv-cache"
set "UV_PYTHON_INSTALL_DIR=%TOOLS%\python"

echo [bootstrap] Step 2/3 -- install portable Python + project deps (2-5 min)
"%UV_BIN%" sync --project "%ROOT%"
if errorlevel 1 (
    echo [bootstrap] ERROR: uv sync failed.
    pause
    exit /b 1
)

echo [bootstrap] Step 3/3 -- smoke-test the ConPort server
"%UV_BIN%" run --project "%ROOT%" python -c "import importlib; importlib.import_module('context_portal_mcp'); print('[bootstrap]   context_portal_mcp imported OK')"
if errorlevel 1 (
    echo [bootstrap] ERROR: ConPort server failed to import.
    pause
    exit /b 1
)

echo.
echo [bootstrap] DONE. Subsequent launches will start in ^< 3 seconds.
echo [bootstrap] You can now point your editor (Windsurf/VS Code/Cursor) at:
echo [bootstrap]   %ROOT%\conport_launcher.cmd
endlocal
exit /b 0
