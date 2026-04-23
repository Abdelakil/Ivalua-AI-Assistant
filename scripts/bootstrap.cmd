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

REM Some corporate Windows setups redirect %TEMP% to C:\Temp which has
REM restrictive ACLs / AV locks that break uv's PE-trampoline rewrites
REM ("Failed to update Windows PE resources ... Access denied"). Keep
REM temp files inside the project folder where the user definitely has
REM write access.
set "TEMP=%TOOLS%\temp"
set "TMP=%TOOLS%\temp"
if not exist "%TEMP%" mkdir "%TEMP%"

REM Enterprise networks with DPI/TLS interception tend to kill long-running
REM parallel HTTPS transfers ("os error 10054"). Tame uv to survive them:
REM   - serialize downloads (fewer concurrent connections for firewalls to kill)
REM   - generous per-request timeout so large wheels (torch 109MB) can finish
REM   - native Windows TLS plays nicer with corp proxy CAs
if not defined UV_CONCURRENT_DOWNLOADS set "UV_CONCURRENT_DOWNLOADS=2"
if not defined UV_HTTP_TIMEOUT          set "UV_HTTP_TIMEOUT=600"
if not defined UV_NATIVE_TLS            set "UV_NATIVE_TLS=1"

REM ---- Corporate PyPI mirror: if pip has a credentialed index URL but uv
REM      doesn't, inject pip's credentials into uv's index so sync works
REM      on locked-down networks (common on enterprise setups).
REM      Strategy: keep UV_INDEX_URL host/path, take only user:pass from PIP.
for /f "usebackq delims=" %%U in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$uv = $env:UV_INDEX_URL; $pip = $env:PIP_INDEX_URL;" ^
    "if ($pip -and $pip -match '^(https?://)([^@/]+:[^@/]+)@' -and $uv -and $uv -notmatch '@') {" ^
    "  $creds = $Matches[2]; Write-Output ($uv -replace '^(https?://)', ('${1}' + $creds + '@')) }" ^
    "elseif ($pip -and $pip -match '@' -and -not $uv) { Write-Output $pip }"`) do (
    set "UV_INDEX_URL=%%U"
)
if defined UV_INDEX_URL (
    REM Mask credentials before logging to avoid leaking secrets into bootstrap.log
    for /f "usebackq delims=" %%M in (`powershell -NoProfile -Command ^
        "$env:UV_INDEX_URL -replace '(https?://)[^@/]+:[^@/]+@','${1}***:***@'"`) do (
        echo [bootstrap]   PyPI index: %%M
    )
) else (
    echo [bootstrap]   PyPI index: ^<default pypi.org^>
)

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
