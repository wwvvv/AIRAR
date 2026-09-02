$ErrorActionPreference = 'Stop'
python -m pip install -r "$PSScriptRoot\requirements.txt"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name AIRAR `
  --icon "$PSScriptRoot\assets\AIRAR.ico" `
  --add-data "$PSScriptRoot\assets;assets" `
  --collect-submodules patoolib --collect-submodules filetype --collect-all PIL `
  --distpath "$PSScriptRoot\dist" --workpath "$PSScriptRoot\build" `
  --specpath "$PSScriptRoot\packaging" "$PSScriptRoot\src\airar.py"
