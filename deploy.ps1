# JSVOC 一键部署脚本 (PowerShell)
# 用法: .\deploy.ps1 -Password "你的密码"
# 或交互式: .\deploy.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$Password = "",

    [string]$Server = "root@8.152.2.222",
    [string]$DeployDir = "/opt/JSVOC"
)

$ErrorActionPreference = "Stop"

# 如果没有传密码，交互式输入
if (-not $Password) {
    $securePassword = Read-Host "请输入 SSH 密码" -AsSecureString
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
}

$PlinkPath = "plink.exe"
$TempDir = "$env:TEMP\jsvoc-deploy"

# 检查或下载 plink
function Ensure-Plink {
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        return (Get-Command plink).Source
    }
    if (Test-Path "$TempDir\plink.exe") {
        return "$TempDir\plink.exe"
    }

    Write-Host "plink 未找到，正在下载..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

    $url = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"
    try {
        Invoke-WebRequest -Uri $url -OutFile "$TempDir\plink.exe" -UseBasicParsing
        Write-Host "plink 下载完成: $TempDir\plink.exe" -ForegroundColor Green
        return "$TempDir\plink.exe"
    } catch {
        # 备用源
        $url2 = "https://github.com/lzs/apt-cyg/raw/master/plink.exe"
        try {
            Invoke-WebRequest -Uri $url2 -OutFile "$TempDir\plink.exe" -UseBasicParsing
            Write-Host "plink 下载完成 (备用源): $TempDir\plink.exe" -ForegroundColor Green
            return "$TempDir\plink.exe"
        } catch {
            Write-Error "无法下载 plink。请手动下载并放入 PATH: https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html"
        }
    }
}

$Plink = Ensure-Plink

Write-Host "=== JSVOC 部署开始 ===" -ForegroundColor Cyan
Write-Host "目标服务器: $Server" -ForegroundColor Gray
Write-Host "部署目录: $DeployDir" -ForegroundColor Gray
Write-Host ""

# 接受主机密钥（首次连接）
Write-Host "[1/5] 确认主机密钥..." -ForegroundColor Cyan
& $Plink -pw $Password -P 22 -ssh $Server "echo connected" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    # 可能需要先缓存主机密钥
    echo "y" | & $Plink -pw $Password -P 22 -ssh $Server "echo connected" 2>$null | Out-Null
}

# 检查运行中的任务
Write-Host "[2/5] 检查正在运行的生成任务..." -ForegroundColor Cyan
$runningTasks = & $Plink -pw $Password -P 22 -ssh $Server @"
cd $DeployDir && docker compose exec -T postgres psql -U postgres -d short_video_ops -t -c "select count(*) from generation_tasks where status in ('queued','running');"
"@ 2>$null
$runningTasks = ($runningTasks -join "").Trim()

if ($runningTasks -and $runningTasks -ne "0") {
    Write-Host "警告: 当前有 $runningTasks 个生成任务正在运行。" -ForegroundColor Yellow
    $confirm = Read-Host "是否继续部署? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "已取消部署" -ForegroundColor Red
        exit 0
    }
}

# 拉取代码
Write-Host "[3/5] 拉取最新代码..." -ForegroundColor Cyan
& $Plink -pw $Password -P 22 -ssh $Server @"
cd $DeployDir && git fetch origin && git reset --hard origin/main
"@ | Write-Host -ForegroundColor Gray

# Docker 构建
Write-Host "[4/5] Docker 构建并重启..." -ForegroundColor Cyan
& $Plink -pw $Password -P 22 -ssh $Server @"
cd $DeployDir && docker compose --progress plain up -d --build
"@ | Write-Host -ForegroundColor Gray

# 检查状态
Write-Host "[5/5] 检查服务状态..." -ForegroundColor Cyan
& $Plink -pw $Password -P 22 -ssh $Server @"
cd $DeployDir && docker compose ps
"@ | Write-Host -ForegroundColor Gray

# 健康检查
$health = & $Plink -pw $Password -P 22 -ssh $Server "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health" 2>$null
if ($health.Trim() -eq "200") {
    Write-Host "后端健康检查通过 (200)" -ForegroundColor Green
} else {
    Write-Host "后端健康检查失败 (HTTP $health)，请检查日志" -ForegroundColor Red
}

$frontend = & $Plink -pw $Password -P 22 -ssh $Server "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:5173/projects" 2>$null
if ($frontend.Trim() -eq "200" -or $frontend.Trim() -eq "307") {
    Write-Host "前端页面检查通过 ($frontend)" -ForegroundColor Green
} else {
    Write-Host "前端页面检查异常 (HTTP $frontend)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Green
Write-Host "线上地址: https://JSVOC.jadejinyuxuan.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用排查命令:" -ForegroundColor Gray
Write-Host "  后端日志: plink -pw *** -ssh $Server 'cd $DeployDir && docker compose logs -f backend'"
Write-Host "  前端日志: plink -pw *** -ssh $Server 'cd $DeployDir && docker compose logs -f frontend-v2'"
