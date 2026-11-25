$ErrorActionPreference = 'Stop'

$destination = 'E:\work\xc'
$name = 'Agent Demo'
$project = Join-Path (Join-Path $destination $name) ($name + '.xcproj')

cli-anything-xcide --json --ide 'I:\xcide' project new $destination $name
if ($LASTEXITCODE -ne 0) { throw "创建工程失败，退出码：$LASTEXITCODE" }

cli-anything-xcide --json --project $project project info $project
if ($LASTEXITCODE -ne 0) { throw "检查工程失败，退出码：$LASTEXITCODE" }

cli-anything-xcide --json --project $project build
if ($LASTEXITCODE -ne 0) { throw "未发现新建且架构匹配的 EXE，退出码：$LASTEXITCODE" }

# 普通 build.ok 表示找到架构匹配的新 PE，compiler.errorCount=null 表示未读取编译诊断。
# 需要真实错误和编译输出时使用 build --diagnostics；详见 AI_CALLING.md。
