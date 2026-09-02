<div align="center">
  <img src="assets/icon.webp" width="132" alt="AIRAR icon" />
  <h1>AIRAR</h1>
  <p><strong>智能解压工具 · 自动识别 · 自动整理</strong></p>
  <p><strong>Smart archive extraction · automatic detection · game-file organization</strong></p>
  <p>
    <a href="https://github.com/wwvvv/AIRAR/releases/latest">下载最新版 / Download</a>
    · <a href="#中文">中文</a>
    · <a href="#english">English</a>
  </p>
</div>

![AIRAR 界面 / AIRAR interface](assets/AIRAR-ui.png)

---

## 中文

AIRAR 是一款面向 Windows 的智能递归解压与游戏文件整理工具。它可以识别伪装后缀和嵌套压缩包，按顺序尝试多个密码，并在解压完成后提取游戏目录与 APK 文件。

### 主要功能

- **拖放解压**：把压缩文件或文件夹直接拖到窗口中。
- **真实格式识别**：根据文件特征识别 ZIP、RAR、7Z、TAR、GZ、BZ2 等格式，包括伪装后缀。
- **递归解压**：自动继续处理解压结果中的嵌套压缩包。
- **多密码匹配**：可在设置中按行保存多个默认密码，AIRAR 会依次尝试。
- **分卷 RAR**：只从 `part1` 首卷开始，避免重复解压与误删分卷。
- **游戏文件整理**：将识别到的游戏目录和 APK 移动到压缩包所在目录。
- **广告规则清理**：支持 `*` 和 `?` 通配符，自动清理匹配的广告文件或目录。
- **存档保护**：`.save`、`.sav`、`persistent`、Ren'Py 文件及常见游戏资源不会被误判为压缩包。
- **密码脱敏**：运行日志不会显示实际解压密码。

### 下载与使用

1. 前往 [Releases](https://github.com/wwvvv/AIRAR/releases) 下载 `AIRAR-v1.0.1-windows-x64.exe`。
2. Windows 如显示来源提示，请核对本页发布的 SHA-256 后再运行。
3. 将压缩文件或文件夹拖入 AIRAR，或使用“选择文件 / 选择文件夹”。
4. 可填写本次优先密码；留空时会自动尝试设置中的默认密码。
5. 点击“开始智能解压”。

> AIRAR 调用系统中可用的解压后端。处理 RAR、7Z 或 AES 加密 ZIP 时，建议安装最新版 7-Zip 或 WinRAR。

### 整理与数据说明

- 原始压缩包及原始分卷会保留。
- AIRAR 只清理本轮成功解压产生的中间内容。
- 游戏目录通过 `.exe`、`UnityPlayer.dll`、`GameAssembly.dll` 等标志识别。
- 默认密码和广告规则保存在 `%APPDATA%\AIRAR\settings.json`。
- 默认密码当前以本地 JSON 文本保存，请勿填写高价值账户密码。
- 同名输出不会直接覆盖，会自动添加数字后缀。

### 从源码运行

环境：Windows 10/11、Python 3.13。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\airar.py
```

### 构建

```powershell
.\build.ps1
```

成品输出到 `dist\AIRAR.exe`。

---

## English

AIRAR is a Windows desktop utility for recursive archive extraction and automatic game-file organization. It recognizes disguised archive extensions, processes nested archives, tries multiple password candidates in order, and keeps detected game directories and APK files in the archive's current directory.

### Features

- **Drag and drop** files or folders onto the application window.
- **Signature-based format detection** for ZIP, RAR, 7Z, TAR, GZ, and BZ2 archives, including disguised extensions.
- **Recursive extraction** of nested archives.
- **Ordered password candidates** configured one per line.
- **Multipart RAR support** that starts from `part1` and skips secondary volumes.
- **Game output organization** for detected game directories and APK files.
- **Ad cleanup rules** with `*` and `?` wildcard matching.
- **Save-file protection** for `.save`, `.sav`, `persistent`, Ren'Py files, and common game resources.
- **Password redaction** in application logs.

### Download and use

1. Download `AIRAR-v1.0.1-windows-x64.exe` from [Releases](https://github.com/wwvvv/AIRAR/releases).
2. Verify its SHA-256 against the value published in the release notes.
3. Drop an archive or folder onto AIRAR, or use the file/folder picker.
4. Enter a one-time priority password, or leave it blank to try saved defaults.
5. Select **Start smart extraction**.

> AIRAR uses an available extraction backend installed on the system. A current version of 7-Zip or WinRAR is recommended for RAR, 7Z, and AES-encrypted ZIP files.

### Data and cleanup behavior

- Original archives and multipart source volumes are preserved.
- Cleanup is limited to intermediate content created by the current successful extraction run.
- Game folders are detected through markers such as `.exe`, `UnityPlayer.dll`, and `GameAssembly.dll`.
- Password candidates and ad rules are stored at `%APPDATA%\AIRAR\settings.json`.
- Saved passwords are currently stored as local JSON text. Do not reuse high-value account passwords.
- Existing output names are not overwritten; AIRAR adds a numeric suffix on collision.

### Run from source

Requirements: Windows 10/11 and Python 3.13.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\airar.py
```

### Build

```powershell
.\build.ps1
```

The executable is written to `dist\AIRAR.exe`.

---

## Project structure

```text
assets/              Brand icon, application icon, mascot, and UI preview
src/airar.py         Application source
requirements.txt     Runtime and build dependencies
build.ps1            Reproducible Windows build script
tests/               Regression tests
```

## Version

Current release: **1.0.1**

## Links

- Website / 检查更新：[https://www.acgxx.com](https://www.acgxx.com)
- Releases：[https://github.com/wwvvv/AIRAR/releases](https://github.com/wwvvv/AIRAR/releases)

## 1.0.1 校验 / Integrity

`AIRAR-v1.0.1-windows-x64.exe`

`SHA-256: 340C5CB4E4D03D7A792DEDE973A7B132F8F73BBE2C8958BA89E2675324179E82`

