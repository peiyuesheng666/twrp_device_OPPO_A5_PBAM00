param(
    [Parameter(Mandatory = $true)][string]$ImagePath,
    [string]$AdbPath,
    [switch]$RebootRecovery
)
$ErrorActionPreference = 'Stop'

if (-not $AdbPath) {
    $AdbPath = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
}
if (-not (Test-Path -LiteralPath $AdbPath)) { throw "adb.exe not found: $AdbPath" }
$image = Get-Item -LiteralPath $ImagePath
$validationPath = [IO.Path]::ChangeExtension($image.FullName, '.validation.json')
if (-not (Test-Path -LiteralPath $validationPath)) {
    throw "Missing offline image validation: $validationPath"
}
$validation = Get-Content -Raw -LiteralPath $validationPath | ConvertFrom-Json
$imageHash = (Get-FileHash -LiteralPath $image.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($validation.sha256 -ne $imageHash -or -not $validation.stock_kernel_matches) {
    throw 'Image hash or structural validation does not match this artifact.'
}
if ($image.Length -gt 67108864) { throw 'Image exceeds the 64 MiB recovery partition.' }

$devices = @(& $AdbPath devices | Where-Object { $_ -match '^\S+\s+(device|recovery)$' })
$matches = @()
foreach ($line in $devices) {
    $serial = ($line -split '\s+')[0]
    $product = ((& $AdbPath -s $serial shell getprop ro.product.device 2>$null) -join '').Trim()
    if ($LASTEXITCODE -eq 0 -and $product -eq 'PBAM00') { $matches += $serial }
}
if ($matches.Count -ne 1) {
    throw "Expected exactly one connected PBAM00; found $($matches.Count)."
}
$serial = $matches[0]
$identity = ((& $AdbPath -s $serial shell id 2>$null) -join '').Trim()
if ($LASTEXITCODE -ne 0 -or $identity -notmatch 'uid=0\(root\)') {
    throw 'The selected PBAM00 ADB shell is not root; no partition was written.'
}
$partition = ((& $AdbPath -s $serial shell readlink -f /dev/block/bootdevice/by-name/recovery 2>$null) -join '').Trim()
if ($LASTEXITCODE -ne 0 -or $partition -ne '/dev/block/mmcblk0p28') {
    throw "Unexpected PBAM00 recovery partition path: $partition"
}

# Pad to the full verified partition size so no stale image tail remains.
$paddedPath = Join-Path $image.DirectoryName 'TWRP-PBAM00-recovery-padded.img'
$payload = [IO.File]::ReadAllBytes($image.FullName)
$stream = [IO.File]::Open($paddedPath, [IO.FileMode]::Create,
    [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $stream.Write($payload, 0, $payload.Length)
    $stream.SetLength(67108864)
    $stream.Flush($true)
}
finally { $stream.Dispose() }
$paddedHash = (Get-FileHash -LiteralPath $paddedPath -Algorithm SHA256).Hash.ToLowerInvariant()

try {
    & $AdbPath -s $serial push $paddedPath /tmp/TWRP-PBAM00-recovery.img
    if ($LASTEXITCODE -ne 0) { throw 'ADB push failed; recovery was not written.' }
    $output = & $AdbPath -s $serial shell 'dd if=/tmp/TWRP-PBAM00-recovery.img of=/dev/block/mmcblk0p28 bs=1048576 && sync' 2>&1
    $flashExit = $LASTEXITCODE
    $output | ForEach-Object { Write-Output $_ }
    if ($flashExit -ne 0) { throw 'Recovery partition write failed.' }
}
finally {
    Remove-Item -LiteralPath $paddedPath -Force -ErrorAction SilentlyContinue
    & $AdbPath -s $serial shell rm /tmp/TWRP-PBAM00-recovery.img 2>$null | Out-Null
}

$record = [ordered]@{
    date = (Get-Date).ToString('o')
    serial = $serial
    device = 'PBAM00'
    partition = $partition
    image = $image.FullName
    image_bytes = $image.Length
    image_sha256 = $imageHash
    bytes_written = 67108864
    padded_sha256 = $paddedHash
    flash_exit_code = 0
    partition_readback_performed = $false
    userdata_formatted_or_backed_up = $false
}
$recordPath = Join-Path $image.DirectoryName 'flash-result.json'
$record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding utf8
if ($RebootRecovery) {
    & $AdbPath -s $serial reboot recovery
    if ($LASTEXITCODE -ne 0) { throw 'Recovery write succeeded, but reboot request failed.' }
}
Write-Output 'Recovery written; no partition readback performed.'
