# detect_machine.ps1 — measure THIS machine's hardware via CIM and emit a
# machine_profile.json the upgrade workflow reasons against. Measured, not guessed:
# this resolves the DDR4-vs-DDR5 question deterministically (DDR generation comes
# from Win32_PhysicalMemory.SMBIOSMemoryType).
#
# Usage:  pwsh -NoProfile -File scripts/detect_machine.ps1 [-OutFile <path>]
# Fields CIM cannot see (PSU wattage, case clearance) are emitted as null with a
# "_needs_manual" note so the build fills them in by hand.

[CmdletBinding()]
param(
    [string]$OutFile = (Join-Path $PSScriptRoot ".." | Join-Path -ChildPath "data\machine_profile.json")
)
$ErrorActionPreference = "Stop"

# SMBIOS memory-type code -> DDR generation label (SMBIOS spec 7.18.2).
$smbiosMemType = @{
    20 = "DDR";  21 = "DDR2"; 24 = "DDR3"; 26 = "DDR4"; 34 = "DDR5"; 35 = "DDR5"
}

$cpu   = Get-CimInstance Win32_Processor | Select-Object -First 1
$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
$gpus  = @(Get-CimInstance Win32_VideoController | Where-Object { $_.AdapterRAM -gt 0 -or $_.Name -notmatch "Basic|Remote" })
$mem   = @(Get-CimInstance Win32_PhysicalMemory)
$disks = @(Get-CimInstance Win32_DiskDrive)

$totalRamGb = [math]::Round(($mem | Measure-Object -Property Capacity -Sum).Sum / 1GB)
$memType = if ($mem.Count -gt 0) { $smbiosMemType[[int]$mem[0].SMBIOSMemoryType] } else { $null }
if (-not $memType) { $memType = "unknown" }
$memSpeed = if ($mem.Count -gt 0) { [int]$mem[0].Speed } else { $null }

$gpu = $gpus | Select-Object -First 1
# Win32_VideoController.AdapterRAM is a signed 32-bit field — it caps at ~4 GB and
# under-reports any card with more VRAM. Prefer nvidia-smi (authoritative) when present.
$gpuVramGb = $null
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
    try {
        $mib = (& nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
        if ($mib) { $gpuVramGb = [math]::Round([int]$mib / 1024) }
    } catch {}
}
if (-not $gpuVramGb -and $gpu -and $gpu.AdapterRAM -gt 0) {
    $gpuVramGb = [math]::Round($gpu.AdapterRAM / 1GB)  # fallback; may under-report >4GB cards
}

# Friendly socket: Win32_Processor.SocketDesignation returns the board silk label
# (e.g. "U3E1"), not the platform socket. Map from the CPU family.
$socketFriendly = switch -Regex ($cpu.Name) {
    "i\d-1[2-4]\d{3}"      { "LGA1700"; break }   # 12th/13th/14th gen Core
    "i\d-1[01]\d{3}"       { "LGA1200"; break }   # 10th/11th gen
    "Ryzen.*7\d{3}"        { "AM5";     break }
    "Ryzen.*[1-5]\d{3}"    { "AM4";     break }
    default                { $cpu.SocketDesignation }
}
# Chipset from the board model string (e.g. "PRO B760-VC" -> "B760").
$chipset = if ($board.Product -match "\b([A-Z]\d{3})\b") { $Matches[1] } else { $null }

$profile = [ordered]@{
    profile_id  = "$($env:COMPUTERNAME.ToLower())-$(Get-Date -Format yyyyMMdd)"
    detected_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    detected_by = "detect_machine.ps1"
    os          = (Get-CimInstance Win32_OperatingSystem).Caption
    cpu = [ordered]@{
        model       = $cpu.Name.Trim()
        socket      = $socketFriendly
        socket_silk = $cpu.SocketDesignation
        cores       = [int]$cpu.NumberOfCores
        threads     = [int]$cpu.NumberOfLogicalProcessors
    }
    motherboard = [ordered]@{
        manufacturer = $board.Manufacturer
        model        = $board.Product
        chipset      = $chipset
        ram_type     = $memType
        ram_slots    = ($mem | Measure-Object).Count
    }
    ram = [ordered]@{
        total_gb  = $totalRamGb
        type      = $memType
        speed_mts = $memSpeed
        modules   = ($mem | Measure-Object).Count
    }
    gpu = [ordered]@{
        model   = if ($gpu) { $gpu.Name.Trim() } else { $null }
        vram_gb = $gpuVramGb
        driver  = if ($gpu) { $gpu.DriverVersion } else { $null }
    }
    storage = @($disks | ForEach-Object {
        [ordered]@{ model = $_.Model.Trim(); capacity_gb = [math]::Round($_.Size / 1GB); media = $_.MediaType }
    })
    psu  = [ordered]@{ watts = $null; rating = $null; _needs_manual = "CIM cannot read PSU; fill in by hand" }
    case = [ordered]@{ max_gpu_len_mm = $null; max_cooler_height_mm = $null; _needs_manual = "measure or look up case spec" }
    goals = [ordered]@{
        primary    = "1440p gaming + local LLM inference"
        priorities = @("gpu_vram", "gpu_perf", "ram_capacity")
    }
    constraints = [ordered]@{ keep_socket = $true }
    exclusions  = @(
        "never read C:\Users\Garre\Workspace\Duracell*",
        "never read C:\Users\Garre\Workspace\malachite\"
    )
}

$outDir = Split-Path -Parent $OutFile
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$profile | ConvertTo-Json -Depth 6 | Set-Content -Path $OutFile -Encoding utf8
Write-Host "[detect_machine] wrote $OutFile"
Write-Host "  CPU: $($profile.cpu.model) ($($profile.cpu.socket))"
Write-Host "  RAM: $($profile.ram.total_gb)GB $($profile.ram.type) @ $($profile.ram.speed_mts)MT/s x$($profile.ram.modules)"
Write-Host "  GPU: $($profile.gpu.model) ($($profile.gpu.vram_gb)GB)"
