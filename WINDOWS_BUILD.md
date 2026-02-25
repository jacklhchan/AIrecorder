# Windows EXE Build Guide

## Prerequisites
- Windows 10/11 x64
- Python 3.11 x64 (recommended)
- FFmpeg in PATH (for MP3 conversion and audio/video merge)
- Optional for system-audio loopback: VB-CABLE or equivalent virtual audio cable

## Build the EXE
From PowerShell in the repo root:

```powershell
.\scripts\build_windows.ps1 -Clean
```

This script will:
1. Create `.venv-windows` (if needed)
2. Install dependencies + `pyinstaller`
3. Build with `packaging/AIrecorder.spec` (Windows entrypoint: `main_windows.py`)

Output executable:

`dist\AIrecorder\AIrecorder.exe`

## Build from macOS using GitHub Actions (no Windows machine needed)
1. Push this project to a GitHub repository.
2. Open `Actions` tab.
3. Run workflow: `Build Windows EXE` (or push to `main`/`master`).
4. Download artifact: `AIrecorder-windows-exe`.
5. Inside the artifact, run `AIrecorder.exe` on Windows.

## Fast rebuild (skip pip install)

```powershell
.\scripts\build_windows.ps1 -SkipDependencyInstall
```

## Notes
- Hotkey is `Ctrl+Shift+R` on Windows.
- "Reveal saved file" opens Windows File Explorer.
- If system audio is silent, verify Windows Sound routing and selected input device.
