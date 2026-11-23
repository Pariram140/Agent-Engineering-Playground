$ErrorActionPreference = "Stop"

function Stop-OnNativeFailure {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        throw "$Message (exit code: $LASTEXITCODE)"
    }
}

Write-Host "Checking Docker availability..."
docker version
Stop-OnNativeFailure "Docker is unavailable. Start Docker Desktop and ensure Linux containers are enabled."

Write-Host "Locating Python..."
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
$PythonExe = $null
$PythonPrefixArgs = @()

if ($PythonCommand) {
    $PythonExe = $PythonCommand.Source
} else {
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PythonLauncher) {
        $PythonExe = $PythonLauncher.Source
        $PythonPrefixArgs = @("-3")
    }
}

if (-not $PythonExe) {
    throw "Python 3.10 or later was not found. Install Python from https://www.python.org/downloads/ and enable 'Add Python to PATH', then reopen PowerShell."
}

$PythonVersion = & $PythonExe @PythonPrefixArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Stop-OnNativeFailure "Unable to start Python."
$VersionParts = $PythonVersion.Trim().Split(".")
if ([int]$VersionParts[0] -lt 3 -or ([int]$VersionParts[0] -eq 3 -and [int]$VersionParts[1] -lt 10)) {
    throw "Python 3.10 or later is required. Found Python $PythonVersion."
}
Write-Host "Using Python $PythonVersion"

Write-Host "Creating Python virtual environment..."
$VenvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    if (Test-Path ".venv") {
        Write-Host "Removing incomplete .venv from the previous setup attempt..."
        Remove-Item ".venv" -Recurse -Force
    }
    & $PythonExe @PythonPrefixArgs -m venv .venv
    Stop-OnNativeFailure "Could not create the virtual environment."
}

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment creation returned successfully, but .venv\Scripts\python.exe was not found."
}

Write-Host "Installing the project and test dependencies..."
& $VenvPython -m pip install --upgrade pip
Stop-OnNativeFailure "Could not upgrade pip."
& $VenvPython -m pip install -e ".[test]"
Stop-OnNativeFailure "Python dependency installation failed."

Write-Host "Running host-side unit tests..."
& $VenvPython -m pytest -q
Stop-OnNativeFailure "Unit tests failed."

Write-Host "Building the sandbox image..."
& $VenvPython -m agent_playground build
Stop-OnNativeFailure "Sandbox image build failed."

Write-Host "Verifying sandbox security controls..."
& $VenvPython -m agent_playground security-check
Stop-OnNativeFailure "Sandbox security checks failed."

Write-Host "Running the intentionally failing demo..."
& $VenvPython -m agent_playground demo
Stop-OnNativeFailure "Demo failure-capture check failed."

Write-Host "Sandbox verification completed successfully."
