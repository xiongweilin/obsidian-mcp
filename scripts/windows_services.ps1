param(
    [string]$Query = '',
    [ValidateRange(1, 100)]
    [int]$Limit = 50
)

$ErrorActionPreference = 'Stop'
$comparison = [System.StringComparison]::OrdinalIgnoreCase
$rows = Get-CimInstance Win32_Service |
    Where-Object {
        [string]::IsNullOrWhiteSpace($Query) -or
        $_.Name.IndexOf($Query, $comparison) -ge 0 -or
        $_.DisplayName.IndexOf($Query, $comparison) -ge 0
    } |
    Sort-Object Name |
    Select-Object -First $Limit |
    ForEach-Object {
        [pscustomobject]@{
            name = $_.Name
            display_name = $_.DisplayName
            state = $_.State
            start_mode = $_.StartMode
        }
    }

ConvertTo-Json -InputObject @($rows) -Depth 3 -Compress
