# setup_env.ps1 - 自动构建 Python 3.8.10 嵌入式环境 (支持 Win7/Win10, x86/x64)

$PythonVersion = "3.8.10"
$Arch = "win32"
if ([Environment]::Is64BitOperatingSystem) {
    $Arch = "amd64"
    Write-Host "[*] 检测到 64 位操作系统" -ForegroundColor Yellow
}
else {
    Write-Host "[*] 检测到 32 位操作系统 (x86)" -ForegroundColor Yellow
}

$ZipUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-$Arch.zip"
$PipUrl = "https://bootstrap.pypa.io/get-pip.py"
$EnvDir = Join-Path $PSScriptRoot "python_env"
$ZipFile = Join-Path $PSScriptRoot "python_embed.zip"
$PipFile = Join-Path $PSScriptRoot "get-pip.py"

# --- 兼容性配置 (针对 Win7) ---
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   正在自动构建便携式 Python $PythonVersion 环境" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 0. 清理旧环境 (防止架构不匹配)
if (Test-Path $EnvDir) {
    Write-Host "[!] 检测到已存在 python_env 目录。将清理旧环境并重新构建..." -ForegroundColor Gray
    Remove-Item -Path $EnvDir -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $ZipFile) {
        Remove-Item -Path $ZipFile -Force -ErrorAction SilentlyContinue 
    }
}


# 1. 创建目录
if (-Not (Test-Path $EnvDir)) {
    New-Item -ItemType Directory -Path $EnvDir | Out-Null
    Write-Host "[+] 创建目录: $EnvDir"
}


# 2. 下载 Python 嵌入版
if (-Not (Test-Path $ZipFile)) {
    Write-Host "[*] 正在下载 Python $PythonVersion 嵌入版..."
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile
}

# 3. 解压
Write-Host "[*] 正在解压到 $EnvDir..."
Expand-Archive -Path $ZipFile -DestinationPath $EnvDir -Force

# 4. 处理 ._pth 文件 (开启 site-packages 支持)
$PthFile = Join-Path $EnvDir "python38._pth"
if (Test-Path $PthFile) {
    Write-Host "[*] 正在配置 $PthFile..."
    $Content = Get-Content $PthFile
    $NewContent = @()
    foreach ($Line in $Content) {
        if ($Line -match "^#import site") {
            $NewContent += "import site"
        }
        else {
            $NewContent += $Line
        }
    }
    # 确保 Lib\site-packages 在路径中
    if (-Not ($NewContent -contains "Lib\site-packages")) {
        $NewContent = @($NewContent[0], $NewContent[1], "Lib\site-packages") + $NewContent[2..($NewContent.Length - 1)]
    }
    $NewContent | Set-Content $PthFile -Encoding Ascii
}

# 5. 下载并安装 Pip
if (-Not (Test-Path $PipFile)) {
    Write-Host "[*] 正在下载 get-pip.py..."
    Invoke-WebRequest -Uri $PipUrl -OutFile $PipFile
}

Write-Host "[*] 正在安装 Pip..."
& "$EnvDir\python.exe" $PipFile

# 6. 安装依赖项
$ReqFile = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $ReqFile) {
    Write-Host "[*] 正在安装项目依赖 (requirements.txt)..."
    & "$EnvDir\python.exe" -m pip install -r $ReqFile --no-warn-script-location
}

Write-Host "==============================================" -ForegroundColor Green
Write-Host "   环境构建成功！请运行 start.bat 启动系统。" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green

# 清理临时文件
# Remove-Item $ZipFile -ErrorAction SilentlyContinue
# Remove-Item $PipFile -ErrorAction SilentlyContinue
