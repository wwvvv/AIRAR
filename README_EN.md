<div align="center">
  <img src="assets/icon.webp" width="132" alt="AIRAR icon" />
  <h1>AIRAR</h1>
  <p><strong>Smart archive extraction · automatic detection · game-file organization</strong></p>
  <p><a href="README.md">简体中文</a> · <a href="https://github.com/wwvvv/AIRAR/releases/latest">Download latest release</a></p>
</div>

![AIRAR interface](assets/AIRAR-ui.png)

## Introduction

AIRAR is a Windows desktop utility for recursive archive extraction and automatic game-file organization. It recognizes disguised archive extensions, processes nested archives, tries multiple password candidates in order, and collects detected game directories and APK files after extraction.

## Features

- **Drag and drop** files or folders onto the application window.
- **Signature-based detection** for ZIP, RAR, 7Z, TAR, GZ, and BZ2 files, including disguised extensions.
- **Recursive extraction** of nested archives.
- **Ordered password candidates** configured one per line.
- **Multipart RAR support** that starts from `part1` and skips secondary volumes.
- **Game output organization** for detected game directories and APK files.
- **Ad cleanup rules** with `*` and `?` wildcard matching.
- **Save-file protection** for `.save`, `.sav`, `persistent`, Ren'Py files, and common game resources.
- **Password redaction** in application logs.

## Download and use

1. Download `AIRAR-v2.3.3-windows-x64.exe` from [Releases](https://github.com/wwvvv/AIRAR/releases).
2. Verify the SHA-256 value published on the release page.
3. Drop an archive or folder onto AIRAR, or use the file/folder picker.
4. Enter a one-time priority password, or leave it blank to try saved defaults.
5. Select **Start smart extraction**.

> AIRAR uses an extraction backend installed on the system. A current version of 7-Zip or WinRAR is recommended for RAR, 7Z, and AES-encrypted ZIP files.

## Data and cleanup behavior

- Original archives and multipart source volumes are preserved.
- Cleanup is limited to intermediate content created by the current successful extraction run.
- Game folders are detected through markers such as `.exe`, `UnityPlayer.dll`, and `GameAssembly.dll`.
- Password candidates and ad rules are stored at `%APPDATA%\AIRAR\settings.json`.
- Saved passwords are currently stored as local JSON text. Do not reuse high-value account passwords.
- Existing output names are not overwritten; AIRAR adds a numeric suffix on collision.

## Run from source

Requirements: Windows 10/11 and Python 3.13.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\airar.py
```

## Build

```powershell
.\build.ps1
```

The executable is written to `dist\AIRAR.exe`.

## Project structure

```text
assets/              Application icon, mascot, and UI preview
src/airar.py         Application source
requirements.txt     Runtime and build dependencies
build.ps1            Windows build script
tests/               Regression tests
```

## Current version

**2.3.3**

- [Release page](https://github.com/wwvvv/AIRAR/releases/tag/v2.3.3)
- [Update website](https://www.acgxx.com)

## File integrity

`AIRAR-v2.3.3-windows-x64.exe`

`SHA-256: 11E2EE6F5F3E50AEBE1A4E809DF47F86756EDB8A8FCB8FD5CB132E2A08F8F092`
