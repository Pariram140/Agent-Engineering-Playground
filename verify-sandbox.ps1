Write-Host "Checking Docker availability..."
docker version
if ($LASTEXITCODE -ne 0) {
    throw "Docker is unavailable. Start Docker Desktop and ensure Linux containers are enabled."
}

Write-Host "Creating Python virtual environment..."
if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}

Write-Host "Installing the project and test dependencies..."
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }

Write-Host "Running host-side unit tests..."
.\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }

Write-Host "Building the sandbox image..."
.\.venv\Scripts\python.exe -m agent_playground build
if ($LASTEXITCODE -ne 0) { throw "Sandbox image build failed." }

Write-Host "Verifying sandbox security controls..."
.\.venv\Scripts\python.exe -m agent_playground security-check
if ($LASTEXITCODE -ne 0) { throw "Sandbox security checks failed." }

Write-Host "Sandbox verification completed."
