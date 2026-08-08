param(
    [Parameter(Mandatory)]
    [string]$Wrapper
)

$ErrorActionPreference = 'Stop'

function Invoke-FixedRemoteCommand {
    param(
        [Parameter(Mandatory)]
        [string]$RemoteCommand
    )

    $output = @()
    $exitCode = 1
    try {
        $output = @(
            & $Wrapper -Command $RemoteCommand 2>$null
        )
        $exitCode = $LASTEXITCODE
    }
    catch {
        if ($null -ne $LASTEXITCODE) {
            $exitCode = $LASTEXITCODE
        }
    }
    [pscustomobject]@{
        exit_code = $exitCode
        lines = $output
    }
}

$systemd = Invoke-FixedRemoteCommand -RemoteCommand (
    'systemctl list-units --type=service --all --no-legend --no-pager --plain'
)

$docker = Invoke-FixedRemoteCommand -RemoteCommand (
    'docker ps --all --format "{{.Names}}\t{{.State}}\t{{.Image}}\t{{.Status}}"'
)

[pscustomobject]@{
    systemd = $systemd
    docker = $docker
} | ConvertTo-Json -Depth 4 -Compress
