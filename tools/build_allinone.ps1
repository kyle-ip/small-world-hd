# Build the all-in-one HD launcher EXE (payload + enable/disable + launch)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$python = "C:\Python311\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python -m pip install --quiet icoextract pillow pyinstaller
try {
  & $python launcher\extract_icon.py
} catch {
  Write-Host "Icon extract skipped: $_"
}

if (-not (Test-Path "launcher\cover.png")) {
  $cnCover = Join-Path (Split-Path -Parent $Root) "small-world-zh-cn\launcher\cover.png"
  if (Test-Path $cnCover) {
    Copy-Item $cnCover "launcher\cover.png" -Force
  }
}

if (-not (Test-Path "payload\Resources\common-hd\AmazonToken.png")) {
  Write-Host "==> HD payload missing. Run: python tools\build_hd_pack.py"
}

$icon = Join-Path $Root "launcher\app.ico"
$cover = Join-Path $Root "launcher\cover.png"
$pyArgs = @(
  "-m", "PyInstaller",
  "--noconfirm", "--clean", "--windowed", "--onefile",
  "--name", "SmallWorld-hd",
  "--distpath", "dist",
  "--workpath", "dist\build\allinone",
  "--specpath", "dist\build",
  "--paths", "launcher",
  "--hidden-import", "steam_find",
  "--hidden-import", "payload_install",
  "--hidden-import", "overlay",
  "--hidden-import", "PIL",
  "--hidden-import", "PIL.Image",
  "--hidden-import", "PIL.ImageTk",
  "--collect-all", "PIL"
)
# Art stays in small-world-hd/payload so this EXE can stay next to SmallWorld-cn.exe.
if (Test-Path $icon) {
  $pyArgs += @("--icon", (Resolve-Path $icon).Path, "--add-data", "$((Resolve-Path $icon).Path);.")
}
if (Test-Path $cover) {
  $pyArgs += @("--add-data", "$((Resolve-Path $cover).Path);.")
}
$pyArgs += @("launcher\app.py")

Write-Host "==> Build SmallWorld-hd.exe"
New-Item -ItemType Directory -Force -Path dist | Out-Null
& $python @pyArgs

if (-not (Test-Path "dist\SmallWorld-hd.exe")) {
  throw "dist\SmallWorld-hd.exe missing"
}

$GameRoot = Split-Path -Parent $Root
$Dest = Join-Path $GameRoot "SmallWorld-hd.exe"
Write-Host "==> Copy to game root: $Dest"
Copy-Item "dist\SmallWorld-hd.exe" $Dest -Force
Get-Item "dist\SmallWorld-hd.exe", $Dest | Format-List FullName, Length, LastWriteTime
Write-Host "Done."
