# Local quality gate. Run before every commit. No CI runs in the cloud.
$ErrorActionPreference = "Stop"

function Step([string]$label, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$label failed" }
}

Step "format" { ruff format --check . }
Step "lint" { ruff check . }
Step "types" { mypy --strict src tests }
Step "tests" { python -m pytest }
