# PowerShell 5.1+ / 7.x
param(
    [Parameter(Position = 0)]
    [string]$Path = '.'
)

$resolvedPath = (Resolve-Path -LiteralPath $Path).ProviderPath

$pattern = '\s*\((?:USA|EU|En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar|En,Fr,De,Es,It,Sv|En,De,Es,Nl,Sv|1999-10-29|1999-05-25|2000-10-26|1999-02-25|En,Fr,De,Es,Sv|1995-10-25|En,Fr,De,Es,It,Nl,Sv,No,Da,Fi|En,Fr,De,Es,It,Nl|En,Fr,Es,Pt|USA, Europe|Virtual Console|En,Fr,De,Nl,Sv,No,Da|U|!|1996-09-24|USA,Brazil|1997-08-11||1998-08-10|UnI|En,Fr,Es,Pt|Unl|Unl|En,Fr,De,Es,It,Fi|En,Fr,De,Es,Nl,Sv|En,De,Es,It|En,Fr,De,Sv|2000-07-24|En,Fr,De,Es,It,Sv|En,Ja,Fr,De|1996-11-21|JP|UK|En,Fr,De,Es,It,Pt|CA|En,Fr,De,Es,It|Unl|En,Fr,De,Es,Nl,Sv,Da|En,Fr,De,It|En,Fr,De,Es,It,Nl,Sv,Da|En,Fr,De,Es|En,Ja,Fr,De,Es|En,Ja||En,Fr|En,Fr,Es,It,Ja|USA,Asia|USA|En,Fr,De|USA,Korea|En,Ja,Fr,De,Es,It,Pt,Pl,Ru|En,Ja|En,Es,It|En,Fr,De,Es,It,Ru|En,Ja,Es|USA, Canada|En,Fr,Es|v\d+\.\d+|En,Ja,Fr,De,Es,It,Ko|En,Es|USA,Canada|En,Zh|En,Fr,De,Es,It,Pt,Ru|En,Ja,Fr,De,Es,It,Ko|En,Fr,Es,Pt|En,Ja,Fr,De,Es,It|v2.02|En,Ja,Fr,Es|En,De|Japan|PAL|NTSC|Europe|World)\)\s*'  # Added (Europe) and (World)

function Get-NormalizedName {
    param([string]$Name)
    $new = [regex]::Replace($Name, $pattern, ' ')
    $new = $new -replace '\s{2,}',' ' -replace '\s+([.\]\)])','$1'
    return $new.Trim()
}

$fileChanges = Get-ChildItem -LiteralPath $resolvedPath -Recurse -File | ForEach-Object {
    $new = Get-NormalizedName -Name $_.Name
    if ($new -ne $_.Name) {
        [pscustomobject]@{
            Old       = $_.FullName
            New       = Join-Path $_.DirectoryName $new
            NewName   = $new
            ItemType  = 'File'
        }
    }
}

$dirChanges = Get-ChildItem -LiteralPath $resolvedPath -Recurse -Directory | ForEach-Object {
    $new = Get-NormalizedName -Name $_.Name
    if ($new -ne $_.Name) {
        [pscustomobject]@{
            Old       = $_.FullName
            New       = Join-Path ([System.IO.Path]::GetDirectoryName($_.FullName)) $new
            NewName   = $new
            ItemType  = 'Directory'
        }
    }
}

# Also consider the root directory itself if requested path points to a folder with a tag.
if ((Test-Path -LiteralPath $resolvedPath -PathType Container)) {
    $root = Get-Item -LiteralPath $resolvedPath
    $newRootName = Get-NormalizedName -Name $root.Name
    if ($newRootName -ne $root.Name) {
        $parent = Split-Path -LiteralPath $root.FullName -Parent
        $dirChanges = @(
            [pscustomobject]@{
                Old       = $root.FullName
                New       = Join-Path $parent $newRootName
                NewName   = $newRootName
                ItemType  = 'Directory'
            }
        ) + $dirChanges
    }
}

$changes = @($fileChanges + $dirChanges) | Where-Object { $_ }
if ($dirChanges) {
    $dirChanges = $dirChanges | Sort-Object { $_.Old.Length } -Descending
} else {
    $dirChanges = @()
}

if (-not $changes) {
    'No changes to be made.'
    return
}

'The following changes will be made:'
$changes | Select-Object ItemType,Old,New | Format-Table -AutoSize

$ans = Read-Host 'Proceed? (y/n)'
if ($ans -match '^[Yy]$') {
    $renameErrors = @()
    foreach ($change in $fileChanges) {
        try {
            Rename-Item -LiteralPath $change.Old -NewName $change.NewName -ErrorAction Stop
            "Renamed file: $($change.Old) -> $($change.New)"
        } catch {
            $msg = "Failed to rename file: $($change.Old) -> $($change.New). Reason: $($_.Exception.Message)"
            $renameErrors += $msg
            Write-Warning $msg
        }
    }
    foreach ($change in $dirChanges) {
        try {
            Rename-Item -LiteralPath $change.Old -NewName $change.NewName -ErrorAction Stop
            "Renamed directory: $($change.Old) -> $($change.New)"
        } catch {
            $msg = "Failed to rename directory: $($change.Old) -> $($change.New). Reason: $($_.Exception.Message)"
            $renameErrors += $msg
            Write-Warning $msg
        }
    }

    if ($renameErrors.Count -gt 0) {
        "`nSome items could not be renamed:"
        $renameErrors | ForEach-Object { " - $_" }
    }
} else {
    'No changes made.'
}
