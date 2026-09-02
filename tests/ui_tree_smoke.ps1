param(
    [Parameter(Mandatory = $true)]
    [string] $ExePath,
    [Parameter(Mandatory = $true)]
    [string] $EvidencePath,
    [Parameter(Mandatory = $true)]
    [string] $ScreenshotPath
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NativeWindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
"@

Start-Process -FilePath $ExePath -WindowStyle Hidden | Out-Null
$deadline = (Get-Date).AddSeconds(60)
$windowProcess = $null
do {
    Start-Sleep -Milliseconds 250
    $windowProcess = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -eq 'AIRAR（智能解压工具）' } |
        Select-Object -First 1
} while (-not $windowProcess -and (Get-Date) -lt $deadline)

if (-not $windowProcess) {
    throw 'Timed out waiting for AIRAR window.'
}

$root = [System.Windows.Automation.AutomationElement]::FromHandle($windowProcess.MainWindowHandle)
[NativeWindowCapture]::ShowWindow($windowProcess.MainWindowHandle, 5) | Out-Null
[NativeWindowCapture]::SetForegroundWindow($windowProcess.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 750
$rect = New-Object NativeWindowCapture+RECT
if (-not [NativeWindowCapture]::GetWindowRect($windowProcess.MainWindowHandle, [ref]$rect)) {
    throw 'GetWindowRect failed.'
}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    $bitmap.Save($ScreenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
$elements = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
)

$rows = New-Object System.Collections.Generic.List[object]
for ($i = 0; $i -lt $elements.Count; $i++) {
    $element = $elements.Item($i)
    $rows.Add([pscustomobject]@{
        Index = $i
        ControlType = $element.Current.ControlType.ProgrammaticName
        Name = $element.Current.Name
        AutomationId = $element.Current.AutomationId
        ClassName = $element.Current.ClassName
        IsEnabled = $element.Current.IsEnabled
    })
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("ProcessId=$($windowProcess.Id)")
$lines.Add("WindowTitle=$($windowProcess.MainWindowTitle)")
$lines.Add("ElementCount=$($rows.Count)")
foreach ($row in $rows) {
    $lines.Add(("{0}`t{1}`t{2}`t{3}`t{4}`t{5}" -f $row.Index, $row.ControlType, $row.Name, $row.AutomationId, $row.ClassName, $row.IsEnabled))
}
$lines | Set-Content -LiteralPath $EvidencePath -Encoding UTF8

try {
    if ($rows.Count -lt 10) { throw "Unexpectedly small Tk window tree: $($rows.Count)." }
    if (-not (Test-Path -LiteralPath $ScreenshotPath)) { throw 'Screenshot was not created.' }
    Write-Output "ui_window_smoke=OK title=yes elements=$($rows.Count) screenshot=$ScreenshotPath"
}
finally {
    $null = $windowProcess.CloseMainWindow()
    Start-Sleep -Seconds 2
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -eq [IO.Path]::GetFileNameWithoutExtension($ExePath) } |
        ForEach-Object {
            if (-not $_.HasExited) { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
        }
}
