# 按功能使用本地模块

根目录：`I:\xcide\data\XC-Module`。将功能转成合适的模块/API 关键词，自行选型；优先工程已有且满足需求、架构和依赖的实现，尊重用户明确指定的模块。

```powershell
# 从本技能目录运行；首次使用先重建当前安装的索引。
$xc = Join-Path (Get-Location).Path 'scripts/xc_modules.py'
python $xc --root 'I:\xcide\data\XC-Module' rebuild
python $xc list 'HTTP'
python $xc search '寻路' --module 'A星寻路模块' --limit 5
python $xc show '12_算法与识别/A星寻路模块/module_astar.h'
```

- `list 关键词` 找包/作者/入口；有明确模块或接口时直接 `search`，不必固定跑完整流程。`--module` 可用模块名或完整入口；同名包按完整路径选定。
- `search 关键词 --module 模块 --limit 5` 查别名、英文声明和 `.xc` 函数；多个词同时匹配。未命中再用 `--raw` 搜原始注释/源码，结果多时用 `--offset` 分页。
- `examples 模块 关键词 --limit 3` 找真实调用；`source 文件 --line 行号 --before 4 --after 12` 读返回位置的上下文，按需扩大范围。
- 需要工程引用/依赖时才 `show 完整入口`。将 `project_import.modules_xml` 的条目合并到现有 `.xcproj`，保留其他引用；`common.xh` 不包含模块头。依赖缺失或重名时，结合源路径和示例确认，不盲选。
- `scope_hint` 和声明只是定位提示；核实当前源码的归属、隐藏区、条件编译、参数及初始化/释放顺序再写调用。索引条目不等于可调用函数或构建证明。
- `source_status` 变化或模块新增/移动时运行 `rebuild`；`stats` 查规模，`verify` 查覆盖/哈希/依赖。重建只改 skill 索引。

完整命令、字段、分类、架构/同名依赖及编码诊断：[按需详情](xc-modules/usage.md)。完整目录 `xc-modules/catalog.md` 仅用于浏览；`catalog.json`、`api.jsonl` 只查询命中内容。覆盖范围以 `stats` 为准，不在入口重复维护计数。
