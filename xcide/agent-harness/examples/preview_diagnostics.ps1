param(
    [Parameter(Mandatory = $true)]
    [string]$Project
)

$ErrorActionPreference = 'Stop'

cli-anything-xcide --json --project $Project preview capture --recipe executable
if ($LASTEXITCODE -ne 0) { throw "本地 EXE 检查预览失败，退出码：$LASTEXITCODE" }

# 预览清单与文件写入工程目录下的 .cli-anything/previews，可直接读取。
