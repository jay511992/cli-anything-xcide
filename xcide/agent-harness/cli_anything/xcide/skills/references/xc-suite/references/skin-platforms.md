# skin-platforms — humbox / hum 两套平台、面板注入、页面绘制流程、坑与自检

> 来源：`xc-代码\界面md\01-humbox-overview.md`、`02-humbox-pages.md`、`03-hum-overview.md`、`04-hum-pages.md`、`05-ai-drawing-guide.md`、`06-copy-ids-reference.md`、`07-pitfalls-and-checklist.md` §5、`08-window-shell-transparency.md` §2、`xcgui-humbox\skill.md`、`xcgui-humbox\references\{architecture,file-map}.md`。

> **窗口属性、窗壳与 `layout.*` 语义不在本文件重复**，见 `interface-xml.md` §2/§4；bkInfoM 与 resource.res 见 `bkinfom-res.md`。

## 1. hum ↔ humbox 必须分离（禁止混搭）

> 源 `xc-代码/skill.md` 硬约束原文：**「禁止 hum 与 humbox 的导航和配色混搭。文案、ID、窗口属性以 06 为准，不臆造。」**

| | **hum** | **humbox** |
|--|---------|------------|
| 产品感 | 创作者 **工具台** | 用户向 **平台客户端** |
| 主窗 | 1180×720 · shaped + `@wnd_bg.png` · 浅色 | 1168×670 · **shadow** · 深色玻璃 |
| 导航 | **左竖栏 180px** | **顶栏 80px** Tab |
| 登录 | 横版 Pro/Gen | 竖版 450×650 |
| 强调色 | 粉/紫；正文近黑 | **`#C5F35F`**；正文白 |
| 页面 | 多内嵌 `main.xml` | 多独立 `layoutPanel` |

声明：`目标项目: hum` 或 `humbox`。**与 humbox 最大差异**：hum 是左侧竖栏工具导航，**不是**顶栏产品 Tab。

**新工具窗不要抄本节任一产品壳**，用 `interface-xml.md` §6 的工具窗令牌。

## 2. humbox 平台（产品「未闻花名UI平台」）

路径 `humbox/布局文件/` · 主 className **`humbox`**。

### 2.1 产品与视觉基线

| 项 | 值 |
|----|----|
| 标题 | 未闻花名UI平台 / 登录窗「… - 登录」 |
| 主窗 | **1168 × 670**，`transparentFlag="shadow"`，`shadowSize="8"` `shadowDepth="75"` |
| 内容设计宽 | 多数面板 `widthT="1024"`，高约 580–640 |
| 风格 | **深色玻璃 / 半透明卡片**；强调色 **亮黄绿** |
| 版本文案 | 未闻花名平台 v2.0 |

强调色（必须）：主强调 / Tab 下划线 / 链接 hover / 光标 = `#FFC5F35F` `#FFBBF327` `#FFB9E800`；主文 = `#FFFFFFFF` 及 60–94% 白；次文 = `#C0FFFFFF` `#ADFFFFFF` `#FFB4B4B4`；深底 / 按钮字 = `#FF171717` `#FF090606` `#FF21241F`；VIP 金棕 = `#FF653D00` `#FF6A503D`；V力红 = `#FFAE0000`。

**视觉风格基线**：暗色玻璃质感（深色半透明窗口、9-patch `login_sd.png` 类边框）；主色暗底 `#270F0F0F`~`#654311423` 半透明白/黑、强调黄绿 `#FFBBF327`（光标/链接悬停 `#FFc5f35f`）、VIP 金紫；圆角 2~12px（小件 2、卡片 6、弹窗 8）；文字层级 正文 `@10`/`@13` 常规灰白（`#B3FFFFFF`），强调 `@10b`/`@13b`，标题 `@15b`/`@18b`，选中纯白 `-1`；悬停态规律 文字变亮（`23(178)`→`23(200)`）、底色提亮 5~10%、`cursor=IDC_HAND`；按下态再提亮或压暗一档 + 透明度微降；图标三态换图（`_01`/`_02`/`_03`），不使用单张图变色。

className 一览：`humbox`（主窗、登录）· `humboxPv`（资源预览）· `humboxUpd`（更新提示）· `mineCard`（我的名片）· `humSetting`（设置窗）· `humHpr`（帮助菜单）· `humboInput`（通用输入）· `vipAc` / `vAgrmt`（VIP / 协议）· `sdkhp` / `SDKUpd`（SDK 相关）· `MdMsg` / `MdNotf`（通知 / 协议）· `SponsorWnd`（赞助）· `flowUI`（悬浮球）· `volAhpl`（火山主题色相关）。

### 2.2 导航架构

```text
login.xml (450×650)  ↓
main.xml (1168×670)
  ├─ 顶栏 h=80：LOGO | 返回 | Tab[首页/资源/皮肤/交互] | 头像 | 菜单/帮助/min/max/close
  └─ main_body
        ├─ home.xml 首页 / res.xml 资源（子：皮肤主题/更新器/验证登录/安装器）
        └─ skin.xml 皮肤 / Interaction.xml 交互
叠层/模态：setting / about / myinfo / avatar / Vv / mine / preview /
  VIP* / updater* / sdk* / msg / UsrTA / sponsor / input / helpWnd / flowing / raking…
```

**主 Tab 快捷键**：1 首页 · 2 资源 · 3 皮肤 · 4 交互；头像 5；菜单 6；帮助 7。

### 2.3 项目结构与文件清单

```text
humbox/
├── 布局文件/   57 个 XML：17 窗口(windowUI) + 18 面板(layoutPanel) + 21 列表项模板 + Test.xml
└── 资源文件/   resource.res（XML 资源清单）+ 230 图片 + font/ 6 字体
```

57 的构成口径见 `interface-xml.md` §1（17 正式窗口 + `Test.xml` 设计器草稿 + 18 面板 + 21 模板）。根目录 `Test.xml`（7KB，1936x1226）是设计器实验草稿，**不要当风格参考**。

**windowUI（独立窗，17）** —— 已合并 `01` §3.1 清单、`06` §A 实读属性表、`file-map` §1（公共窗口属性语义见 `interface-xml.md` §4）：

| 文件 | className | content | 尺寸 | windowType | transparentFlag | padding | 用途 / 备注 |
|------|-----------|---------|------|------------|-----------------|---------|------|
| `main.xml` | humbox | 未闻花名UI平台 | 1168×670 | — | **shadow** | — | 主壳 |
| `login.xml` | humbox | 未闻花名UI平台 - 登录 | 450×650 | — | shaped | 15,12,15,18 | 登录 |
| `mine.xml` | mineCard | — | 290×243 | modalWindow | shaped | 17,30,17,24 | 用户名片 |
| `preview.xml` | humboxPv | pv | 1572×850 | modalWindow | shaped | — | 资源预览 |
| `VIP.xml` | vipAc | — | 702×362 | modalWindow | shaped | 1,1,1,1 | 开通会员 |
| `VIP_agrmt.xml` | vAgrmt | — | 640×220 | modalWindow | shaped | — | 会员协议 |
| `updater.xml` | humboxUpd | updater | 336×432 | — | shaped | 8,5,8,11 | 更新气泡 · topmost |
| `sdk.xml` | sdkhp | 未闻花名引擎SDK | 800×480 | — | shaped | — | SDK 任务记录 · 日志窗 |
| `SDKupdate.xml` | SDKUpd | SDKUpd | 650×480 | modalWindow | shaped | 8,5,8,11 | SDK 环境更新弹窗 |
| `settingWnd.xml` | humSetting | — | 680×520 | modalWindow | shaped | — | 完整设置（左导航） |
| `helpWnd.xml` | humHpr | — | 200×388 | modalWindow | shaped | 23,20,23,26 | 帮助菜单浮窗 |
| `msg.xml` | MdMsg | — | 500×320 | modalWindow | shaped | 15,12,15,18 | 系统通知 |
| `UsrTA.xml` | MdNotf | — | 660×490 | modalWindow | shaped | 15,12,15,18 | 用户协议 |
| `sponsor.xml` | SponsorWnd | 0 | 716×376 | modalWindow | shaped | 7,5,7,9 | 赞助（QQ 936599025、10 V力值+10积分/元） |
| `input.xml` | humboInput | — | 480×507 | modalWindow | shaped | — | 多行输入 |
| `flowing.xml` | flowUI | flowUI | 42×40 | — | shaped | — | 悬浮球 · topmost |
| `vol_bg.xml` | volAhpl | — | 880×500 | modalWindow | shaped | — | 火山MFC窗口组件快速处理弹窗 |

**layoutPanel（嵌入页，18）**：

| 文件 | 用途 | 设计尺寸 |
|------|------|----------|
| `home.xml` | 首页卡片墙 | 1024×600 |
| `res.xml` | 资源 Tab 壳 | 1024×580 |
| `res_page.xml` | 资源 listView | 1024×580 |
| `skin.xml` | 皮肤 | 1024×580 |
| `Interaction.xml` | 交互工具 | 1024×580 |
| `raking.xml` | 排行榜 | 1024×580 |
| `rk_total_rk.xml` | 榜类型切换条 | 460×60 |
| `setting.xml` | 右侧轻设置抽屉 | 1024×640 |
| `about.xml` | 关于 | 1024×1100 |
| `myinfo.xml` | 我的信息 | 1024×1000 |
| `avatar.xml` | 头像编辑 | 1024×640 |
| `Vv.xml` | V力详情 | 1024×640 |
| `loading.xml` | Loading | — |
| `layoutFrame.xml` | 更新说明阅读板 | （无 widthT，勿套 1024） |
| `updater_details.xml` | 更新详情容器 | 400×420 |
| `progress.xml` | 进度反馈 | 1024×640 |
| `dropfile.xml` | 拖放确认 | 1024×640 |
| `mydata.xml` | 数据占位 | 500×500 |

`skin.xml` 17.6KB 最复杂表单页；`Interaction.xml` 25KB 最大；`layoutFrame.xml` 有 `_up_title`/`_up_time`/`_up_content`/`_up_update`/`_up_prog`/`_up_task_text`/`_up_task_prec` 七个宿主填充槽；`loading.xml` = 300x300；`dropfile.xml` 文案「拖入文件到窗口内 / 按下 ESC 取消」。

**模板（21）**：`res_item_temaplate_{free,member,point,private,unlocked,VIP}.xml` = 资源卡（6 种角标）；`raking_{first,second,third,other}_{v,point,pet}.xml` = 榜单行（12）；`sdk_template.xml` = SDK 任务行；`updater_list_itemTemp.xml` = 更新列表行；`combobox_template.xml` = 下拉项。

listView 模板 6 个（资源卡片 318x294，字段：缩略图/name1）；list 模板 14 个（排行 12 + sdk_template + updater_list_itemTemp）；listBox 模板 1 个（`combobox_template.xml`，字段 name1，`@10` 白字左对齐 padding 16）。

**页面类型速查**：`windowUI` = main login mine preview VIP VIP_agrmt updater sdk SDKupdate settingWnd helpWnd msg UsrTA sponsor input flowing vol_bg；`layoutPanel` = home res res_page skin Interaction raking rk_total_rk setting about myinfo avatar Vv loading layoutFrame updater_details progress dropfile mydata；`xc_template_*` = 全部 res_item_*、raking_*、sdk_template、updater_list_itemTemp、combobox_template。

### 2.4 主壳骨架与面板注入架构（必须还原）

```text
windowUI 1168×670 shadow
 └ layoutEleUI name=main  fill×fill
     ├ 顶栏 h=80  space=24  padding=24,0,20,0：shapePicture LOGO 40×40 · id=1 导航（返回32 + radio 首页/资源/皮肤/交互，宽52）
     │   · id=2 头像按钮 32×32 float · id=3 系统区（菜单/帮助/min/max/close）
     └ main_body 宽 fill 高 :1   ← 装载各 layoutPanel
```

选中 Tab：字色变亮 + **底部 2px 黄绿短条**。

```xml
<windowUI className="humbox">
  <layoutEleUI name="main">                      ← 根容器
    <layoutEleUI ...>标题栏：LOGO + 4个导航单选按钮(groupID=0) + 用户/菜单/帮助 + min/max/close</layoutEleUI>
    <layoutEleUI name="main_body" layout.height=":1" layout.width="fill" />   ← 页面槽位（空）
  </layoutEleUI>
</windowUI>
```

**页面切换机制**（宿主运行时完成，布局文件只负责声明）：① 四个导航按钮 `首页/资源/皮肤/交互` 是 `buttonType="radio" groupID="0"`，各带快捷键 tooltip（快捷键[1]~[4]）；② 宿主监听单选切换，把对应面板（home.xml/res.xml/skin.xml/Interaction.xml）注入 `main_body`；③ 页面内部的二级导航（如 skin.xml 的 自定义加载/一键加载）用 `groupID="3"` 单选 + `bindEle` 机制。

**bindEle 显示切换**（布局内声明式切换，无需宿主代码）：

```xml
<buttonUI bindEle="@ID_皮肤_自定义加载" buttonType="radio" groupID="3" ... />   ← 导航单选
...
<layoutEleUI id="@ID_皮肤_自定义加载" showT="true">内容A</layoutEleUI>           ← 被控面板A
<layoutEleUI id="@ID_皮肤_一键加载"   showT="false">内容B</layoutEleUI>          ← 被控面板B
```

选中带 `bindEle="@ID_X"` 的按钮 → 显示 `id="@ID_X"` 的面板、隐藏同组其他。符号 ID 在 resource.res type_id 注册。嵌套版本（Interaction.xml）：子面板自身又是新单选组的 bindEle 容器，形成 `@ID_更新器交互` → `@ID_更新器交互_程序配置` → `@ID_更新器交互_程序配置_配置详细` 三层。

**groupID 分配**：0 主窗口导航（首页/资源/皮肤/交互）· 2 资源页内导航 · 3 皮肤页内导航 · 4 交互页内导航。新增页面内导航顺延新号，不与现有冲突。

**间距与圆角节奏 / 字体 token**：页面 padding `40,32,40,48`（首页），排行更宽约 80；卡片间距 24–28；表单行距 12；顶栏高 80（主）/ 32（子导航）；资源卡 item 318×294，列距 24，行距 36；首页卡 min 215×292；圆角 卡片 2–6、输入 6–8、主 CTA 16–20、窗 8–12。

字体 token：`@8_yh` `@9` `@9b` `@9_num` `@10` `@10b` `@11` `@12` `@12b` `@13` `@13b` `@13_num` `@15b` `@16b` `@18b` `@26b`

**高频资源（按模块）**：品牌 `LOGO.svg` `logo_lg.svg` `logo_about.svg` `msglogo.svg`；登录 `lgbg.png` `login_sd.png` `eyes_*.svg` `ckd.svg` `close1~3.svg`；导航 `navbtn_icon_{skin|update|login|install}_01~03.svg`；我的 `mine_bg.png` `mine_Vicon_*.svg` `mine_vip_bg.png`；预览 `defAuthor.jpg` `pv_icon_01.svg` `pv_res_unlock.svg`；排行 `first/second/third_icon_*.svg` `raking_icon_*.svg`；VIP / 更新 / 赞助 `vip_icon_*` `updater_*` `sponsor_*`。完整图资源列表见仓库 XML 内 `@xxx` 引用。

### 2.5 逐页结构

`login.xml` — 登录 450×650：`windowUI humbox「未闻花名UI平台 - 登录」shaped + padding=15,12,15,18`，背景 `@lgbg.png` + 阴影 `@login_sd.png` · 圆角 8；顶条 → close（右上 float）；内容区 spaceRow≈20：id=9 品牌图占位 elementUI · id=1 edit tips「输入你的账号」h=40 caret `#BBF327` 圆角6 · id=2 密码 + id=3 显隐眼标 · id=5「我已阅读并同意」+ id=8《用户协议》(hover `#c5f35f`) · id=4「登录」h=40 字 `#21241f` · 「登录遇到问题？」+ id=7联系客服 / 「没有账号？」+ id=6注册账号。**气质**：竖屏卡片、半透输入框、主钮浅色实心。

`main.xml` — 主窗：见 §2.4；`main_body` 为空槽，运行时装载下方页面。

`home.xml` — 首页 1024×600：`layoutPanel` → 根 `fill` `spaceRow=28` `padding=40,32,40,48`；`layoutFrameUI home_01` 横向滚动卡片带（卡1 炫光多色渐变 → home_02 min 215×292；卡2~4 → home_03/04/05；卡5 禁用「敬请期待」→ home_12）；`home_06` 高 30%（`home_07` 左大块 min≈458×150 + 右 2×2 快捷钮 → home_08 ~ home_11）。**画法**：上 ~70% 横滑大卡（圆角 2）；下 30% 左横幅 + 右四宫格入口。

`res.xml` + `res_page.xml` — 资源：`res.xml` 顶导航 h=32（皮肤主题 / 更新器 / 验证登录 / 安装器）+ 帮助图标 +「出现任何问题，请随时与我们联系反馈」，`name=资源_布局` → 动态装入内容；`res_page.xml` = `listViewUI itemSize≈318×294 colSpace=24 rowSpace=36`。XML 里后三个 Tab 的 `bindEle` 都指向 `@ID_皮肤_一键加载`（设计器遗留）；画界面以**可见文案**为准。

资源卡模板 `res_item_temaplate_*` 统一约 **286×308** 视觉区：上=缩略图封面；中=hover「查看详细」；下=标题 + 作者/QQ；角=VIP / 积分价 / 免费 / 会员 / 私有 / 已解锁。`point` 模板额外右下角价格胶囊。

`skin.xml` / `Interaction.xml` — 同构工具页：顶 32px pill radio（bindEle 切子面板）+ 右上反馈文案；主体 左表单（宽权重 `:5`）| 右「使用说明」（`:2`，min≈340）。表单行：左标签宽约 **140**（`border`/`padding`），控件高 40；主 CTA 宽约 **260**、高 40 —— 浅亮底 + 深色字。

| 页 | 子 Tab | 主 CTA |
|----|--------|--------|
| skin | 自定义加载 / 一键加载 | 「确认皮肤并授权」/「一键授权皮肤」 |
| Interaction | 更新器交互 / 验证交互 / 安装器交互 | 「解析更新模板」/「解析验证模板」；更新器另有「打包数据」「生成配置」「确认生成更新器」 |

`raking.xml` — 排行榜：横排 space=16 padding≈80,32,80,80；左装饰条 shapePicture 宽`:1`；左栏 宽140（`rk_myrk` 头像/昵称/成长值/排名 + 底条）；右栏 宽`:6`（`listUI rk_list` 行高60、行距6、表头28）+ 底 `rk_type`；右装饰条 宽`:1`。`rk_total_rk.xml` = 横向 pill —— **V力值榜**（默认）/ 宠物榜 / 积分榜 / 解锁榜 / 兑换券榜（`rk_list_01~05`）。列表模板：`first/second/third` = 奖牌图标替换数字，`other` = 数字名次；后缀 `_v` / `_point` / `_pet` 列字段不同。

`mine.xml` — 名片 290×243：用户区 头像 / 名「未闻花名UI」/ V标 / 进度条 / 文案；VIP 条 +「续费」；「查看我的信息」。背景 `@mine_bg.png`；VIP 金条 `@mine_vip_bg.png`。

`preview.xml` — 预览 1572×850 · modal · humboxPv：半透明遮罩底；id=3 顶条 320×60「资源的名称」+「使用」胶囊（圆角16）；id=1 主卡宽 1440 · 标题「资源预览的标题」（layoutFrame 预览滚动 + 右侧竖列 id4作者 / id5类型 / id6编号 / id8兑换，各约44×76）；id=7 关闭 tip「隐藏预览详细」。

`VIP.xml` — 702×362 · vipAc：暗金渐变卡 · 标「未闻花名平台VIP」；头 头像槽 /「未闻花名」/ 有效期占位 / 关闭；权益三行（装扮 / 资源特权 / 畅享）；套餐 radio 自定义月数 · 1个月(默认100积分) · 2/3/6/12月；「开通会员」(字 `#653D00` 圆角20) +《会员服务协议》。

设置系：`setting.xml`（轻抽屉）右侧浅色条 = 系统设置 · 加入群聊 · 关于我们 · 更新检查 · 查看平台用法 · 充值&赞助 · 「未闻花名平台 v2.0」。`settingWnd.xml`（完整 680×520 · humSetting）左导航 **通用 / SDK / 外观 / 系统**；右滚动。通用含 开机启动、背景音乐、关闭提示、显示日志…；外观 主题缩略 radio **138×110**（云野仙踪默认、森澜祈光、森澜雾境、苏暖暖Ⅰ…）。

更新系：`updater.xml` = 336×432 白卡片（插画 + 文案 +「查看详细」）；`layoutFrame.xml` = `_up_title` / `_up_time` / `_up_content` /「立即更新」/ 进度；`updater_details.xml` = 详情容器；`updater_list_itemTemp.xml` = 列表行。

`sdk.xml` — 800×480：顶栏「任务记录」+ 清空 / 横排 / 纵排 / 关闭；下半 list 任务表 + 只读日志 edit。

`myinfo.xml`：大标题「我的信息 / MY INFO」→ 账号概况卡 → V力·解锁 → 宠物四格 → 绑定信息 → CTA「联系客服」。`about.xml`：ABOUT US → 成员卡（未闻花名、书香）→ QQ 群 → Copyright © HUMUI。

| 其它短页 | 要点 |
|------|------|
| `avatar.xml` | 头像编辑，大圆角预览 |
| `Vv.xml` | V力详情 + scrollView |
| `loading.xml` | 居中占位（无固定 widthT） |
| `flowing.xml` | 窗 42×40，图标约 32，`flowUI` |
| `msg.xml` | 「系统通知」+ 正文 +「取消」「确认」 |
| `UsrTA.xml` | 协议正文滚动 · MdNotf |
| `sponsor.xml` | 赞助插画 + 支付入口 |
| `input.xml` | 多行输入 · humboInput |
| `helpWnd.xml` | 9 项菜单（安装器说明/插件说明禁用） |
| `dropfile.xml` / `progress.xml` | 拖放确认 / 进度反馈 |
| `VIP_agrmt.xml` | 短协议窗 · vAgrmt |

### 2.6 命名约定全集（宿主按 name / @ID_ 查找）

| 模式 | 示例 | 用途 |
|---|---|---|
| `{页面}_NN` | `home_01`..`home_12`、`myinfo_00`..`16`、`vv_01..03` | 设计器自动生成的结构名 |
| `{页}_{区块}_{控件}_{类型}` | `皮肤_自定义加载_对接程序_编辑框`、`皮肤_一键加载_算法类型_组合框`、`交互_更新器_确认生成更新器_按钮` | 代码驱动的功能元素 |
| `{页}_nav_{项}` | `皮肤_nav_自定义加载`、`皮肤_nav_一键加载` | 页内导航 |
| 槽位前缀 `_up_` | `_up_title` `_up_time` `_up_content` `_up_update` `_up_prog` `_up_task_text` `_up_task_prec` | layoutFrame.xml 的通用更新帧槽位（宿主填充） |
| `main` / `main_body` | — | 主窗口根容器与页面槽（**保留名**） |

资源文件名：图标多态三份 `_01`=正常、`_02`=悬停、`_03`=按下（如 `navbtn_icon_skin_01/02/03.svg`、`close1/2/3.svg`）；头像框 `头像框{1,2,3}_{尺寸}x{尺寸}_{状态序号}.{png|svg}`，尺寸 32/80/120/160；拼音/英文小写下划线命名为主。

符号 ID（type_id）：`ID_{模块}_{功能}[_{子级}]`，模块∈{皮肤,更新器交互,验证交互,安装器交互}。层级用下划线延伸：`ID_更新器交互_程序配置_配置详细`。

### 2.7 依赖关系图

```text
resource.res ──注册──> 全部图片/字体/符号ID/命名样式（布局以 @名 引用）
main.xml (humbox)
 ├─ main_body 槽位 <── home.xml / res.xml / skin.xml / Interaction.xml（主导航 groupID=0 切换）
 │    ├─ res.xml ──bindEle──> 资源子面板（@ID_* 系）+ res_item_temaplate_*.xml 卡片 + combobox_template.xml
 │    ├─ skin.xml ──bindEle──> @ID_皮肤_自定义加载 / @ID_皮肤_一键加载 两个子面板
 │    ├─ Interaction.xml ──bindEle──> @ID_更新器交互 / @ID_验证交互 / @ID_安装器交互（各自再嵌套_使用说明/_程序配置/_配置详细）
 │    │    └─ 关联窗口: sdk.xml(SDKUpd) / vol_bg.xml(volAhpl 火山MFC)
 │    └─ home.xml ──横滚卡片──> home_item1_bg.png 等资源
 ├─ 弹窗族: login.xml(humbox) / msg.xml(MdMsg) / mine.xml(mineCard) / myinfo.xml→avatar.xml / VIP.xml(vipAc)→VIP_agrmt.xml(vAgrmt)
 │   / settingWnd.xml(humSetting)→setting.xml / preview.xml(humboxPv) / input.xml(humboInput) / UsrTA.xml(MdNotf)
 │   / helpWnd.xml(humHpr) / sponsor.xml(SponsorWnd) / Vv.xml 面板 / sdk.xml(sdkhp) / SDKupdate.xml(SDKUpd)
 ├─ 更新器链: updater.xml(humboxUpd) ──> layoutFrame.xml(_up_* 槽) / updater_details.xml + updater_list_itemTemp.xml
 ├─ 工具面板: progress.xml / dropfile.xml / loading.xml
 ├─ 排行榜链: raking.xml ──> rk_total_rk.xml ──> raking_{first,second,third,other}_{pet,point,v}.xml
 └─ 桌面悬浮: flowing.xml(flowUI)
Test.xml = 独立草稿（引用 Vv_* 资产实验，与上述链无正式关联）
```

找文件最快方式：改主界面标题栏/导航 → main.xml；改某页面内容 → 主页面板四文件；改弹窗 → 按 className 找；改列表行/卡片外观 → 模板；加图片/字体/ID/复用样式 → `资源文件/resource.res` 对应 type_ 节；查某资源是否被用 → 在 `布局文件/` 全文搜 `@资源名`；查某元素被宿主怎么用 → 全文搜元素 name。

### 2.8 已知问题清单（修改时留意）

1. `flow_ic1.svg`、`home_btn3_icon_01.svg`：布局中引用但**文件不存在**（悬空引用，运行时不显示）

2. resource.res 注册了 `pv_vip.jpg` 但实际文件是 `pv_vip.png`（jpg 条目失效）；`banner.jpg` 注册但未随包分发

3. `lgbg.png` 被 login.xml 的 bkInfoM 引用但**未在 resource.res 注册**（login 能显示说明宿主可能宽松解析，但按规范应补注册）

4. `11.png`、`22.png`、`en.ttf` 为未引用的孤儿文件（可清理，但先与用户确认）

5. `Test.xml` 是设计器草稿，其中元素与资源（Vv_* 资产）是实验性的——**不要把 Test.xml 当作规范参考**

## 3. hum 平台（产品「未闻花名UI」）

路径 `hum/布局文件/` · 主 className **`HUMUIMain`**。

### 3.1 产品与视觉

| 项 | 值 |
|----|----|
| 标题 | 未闻花名UI（文案亦见「未闻花名UI平台/设计」） |
| 主窗 | **1180 × 720**，`shaped` + **`@wnd_bg.png`**，padding **24** |
| 风格 | **浅色圆角工具台**；左导航 180 + 右内容 |
| 版本 | Bate 0.1 · 时间占位 2024-10-20 |
| 定位 | 炫彩 UI 资源平台 + **合并 / 皮肤 / 更新器** 开发者工具 |

强调色：Pro 登录「设计」`#FFFD687E` 粉红；Gen 登录「设计」/ QQ 强调 `#FFCA8BFF` 淡紫；主字 `#FF181D27` `#FF171717`；次字 / 标签 `#FF9B9EA2` `#FF797D86` `#FF999DA9`；链接蓝 `#FF0079f4` `#FF008efa`；等级金牌 `#FFDF8804` `#FF654E01`；兑换券强调 `#FFC9405C`。

命名色 token：`@main_主要文本色` `@标题颜色` `@子标题颜色` `@白色`。

className：`HUMUIMain`（主窗）· `HUMUILGPro` / `HUMUILGGen`（Pro / 普通登录）· `HUMSetting`（设置）· `HUMUI`（多数模态）· `flowUI`（悬浮球）。

**hum 窗表（产品）** —— 已合并 `08` §2 窗壳实读表与 `06` §E 窗口属性表；路径 `hum/布局文件/`（`通用元素模板.xml` 为设计板 `windowStyle=2031`，勿当运行壳）：

| 文件 | className | content | 尺寸 | windowType | flag | padding | 窗壳底 | 备注 |
|------|-----------|---------|------|------------|------|---------|--------|------|
| `main.xml` | HUMUIMain | 未闻花名UI | 1180×720 | — | shaped | 24,…（06：`24`） | **`@wnd_bg.png`** | 产品主窗 |
| `login_Pro.xml` | HUMUILGPro | 未闻花名UI | 908×508 | — | shaped | 30,…（06：`30`） | `@lg_wnd_bg.png` | 左插画右表单 |
| `login_Gen.xml` | HUMUILGGen | 未闻花名UI | 880×460 | — | shaped | 1,…（06：`1`） | `22(-1)` 实心 | 左表单右插画 · 无图也可 |
| `set.xml` | HUMSetting | — | 750×480 | modal | shaped | 15,…（06：`15,11,15,19`） | `@set_wng.png` | 设置 |
| `msg` / `qr_*` | HUMUI | 未闻花名UI | msg 600×276 · qr_* 322×372 | modal | shaped | 21,…（06：多为 `21,11,21,31`） | `@md_wnd_bd.png` | 模态 |
| `rak_detail.xml` | HUMUI | 未闻花名UI | 440×542 | modal | shaped | 21,… | `@md_wnd_bd1.png` + 装饰 | 成长值明细 |
| `fb.xml` | HUMUI | 未闻花名UI | 342×472 | modal | shaped | 1,…（源不一致：06 归入「多为 `21,11,21,31`」） | `@fb_wnd_bd.png` | 反馈加群 |
| `about.xml` | HUMUI | 未闻花名UI | 520×440 | modal | shaped | — | 弱壳 | **勿学空壳** |
| `flowing.xml` | flowUI | flowUI | 42×40 | — | shaped | — | 填充色 | 浮球 |

模态尺寸：about 520×440 · msg 600×276 · fb 342×472 · qr_* 322×372 · rak_detail 440×542。

复刻 hum 主窗骨架：

```xml
<windowUI windowStyle="0" transparentFlag="shaped" transparentAlpha="255"
  dragWindow="true" dragBorder="false" overlayBorder="true"
  enableLayout="true" center="true" padding="24,24,24,24"
  bkInfoM="{99:1.9.9;98:1(0,1);3:2(15)4(@wnd_bg.png);5:2(15)3(23,23,23,23)10(1)7(1)11(3)16(1)12(419430400)13(25)9(8,8,8,8);}">
```

`wnd_bg.png` → `resource.res` `<type_image>` + 运行目录 `img\`。

源码实读：`Downloads\hum\布局文件\main.xml`（`@wnd_bg.png`）、`Downloads\hum\资源文件\img\wnd_bg.png`、`Downloads\humbox\布局文件\main.xml`（shadow）。

### 3.2 导航架构

```text
login_Pro (908×508)  或  login_Gen (880×460)      ↓
main HUMUIMain (1180×720)
  ├─ 启动页（默认隐藏）：居中 LOGO +「未闻花名UI」
  ├─ 左侧导航 w=180：MENU 资源 | 资源交互 | 皮肤 | 更新器 | 安装器 | 排行榜 · SOFT 软件市场 | 下载管理 · 底「关于&反馈」
  └─ 右侧内容 :1：标题栏（置顶 / 设置 / 菜单 | min / close）→ 用户条（VIP、宠物、积分、解锁、兑换券、刷新）
       → 页面栈 @ID_main（radio bindEle）→ 「我的信息」覆盖页
悬浮球 flowing ↔ 恢复主窗      模态：set / about / msg / fb → qr_* / rak_detail / UI_preview
```

**文件清单（26）**

窗口/悬浮：`main.xml` 主 HUMUIMain 1180×720（几乎所有业务页内嵌于此）· `login_Pro.xml` 入口 HUMUILGPro 908×508 · `login_Gen.xml` 入口 HUMUILGGen 880×460 · `flowing.xml` 浮 flowUI 42×40 · `set.xml` 模态 HUMSetting 750×480 · `about.xml` 模态 HUMUI 520×440 · `msg.xml` 模态 HUMUI 600×276 · `fb.xml` 模态 HUMUI 342×472 · `qr_group.xml` 模态 HUMUI 322×372 · `qr_qq.xml` 模态 HUMUI 322×372 · `rak_detail.xml` 模态 HUMUI 440×542。

面板：`UI_preview.xml` 1920×1080 · `inner_notify.xml` 800×300 · `UP_progress_page.xml` 460×178 · `通用元素模板.xml` 设计板。

模板：`UI_template_1~4.xml`（资源卡：积分兑换 / 会员专享 / V8专享 / 限时免费）· `raking1~5_listbox_template.xml`（等级 / 积分 / 解锁 / 兑换券 / 宠物榜行）· `up_tmp_template.xml` / `_sel.xml`（更新器模板未选/选中）。

### 3.3 主壳骨架（必须还原）

```text
windowUI 1180×720 shaped  padding=24  bg=@wnd_bg.png   ← 必须进 resource.res / img\
 └ 根 layout fill
     ├ 启动页（可隐藏）
     ├ 左侧导航 w=180  padding≈12,30,12,10：LOGO28 + 标题 · MENU 分组 + radio 导航项 h=32 spaceRow=6
     │   · SOFT 分组 + 两项 · 底「关于&反馈」h=56 渐变大钮
     └ 右侧 :1：标题栏 h=28 右对齐图标 34×28 · 用户条 h=40 浅灰 chip 圆角3 · @ID_main 页面区 :1
```

导航项：左图标区约 32 + 文案；未选中浅透底，选中浅橙/米色底 + 深字。

其他窗壳：登录 Pro `@lg_wnd_bg.png` · 模态 `@md_wnd_bd.png` · Gen 可实心填充。

**设计令牌摘要**：字体 `@7`–`@14b` `@18b` `@21b`；数字 `@number_7`–`@number_12b`；装饰大字可见 `@38b` `@50b`。间距：主窗外 padding **24**；模态常配合 `@md_wnd_bd.png` 边距约 `21,11,21,31`；导航项高 **32**，spaceRow **6**；资源卡 **290×222**（封面区约 266×164）；排行行高 **66**；登录主钮圆角 **10**，工具钮约 **6**。窗控图标族 `mini` `close` `top` `set` `menu` + 态变体；登录 `close_lg*`；模态 `close_md*`。导航图标 `nav1`–`nav8` 与 `_0` 未选中态。

### 3.4 逐页结构

`login_Pro.xml` — 908×508 · HUMUILGPro：左 `:1` 品牌区（「未闻花名UI平台」+ Pro 徽章；插画文案 随心 / 便捷 / 创意 / 随行 + HUMUI）；右 w≈400 表单（close；「探寻」+「设计」(`#FD687E`)+「的魅力」；「请登录. 遇到问题？」+ link「联系我们」；edit 账号 + user 图标；edit 密码 + pwd + 显隐 check；button「登录」h≈42 圆角10；「还没有账号？」+ link「点我注册账号。」）。背景窗图 `@lg_wnd_bg.png`。

`login_Gen.xml` — 880×460 · HUMUILGGen：左 w≈378（logo_login +「未闻花名UI」|「普通版」；「欢迎回来」+ grin.svg；表单同 Pro（控件 id 1–6），登录钮 h≈38）；右 `:1` `@lg_bg.png`（close；「探寻/设计(`#CA8BFF`)/的魅力」+ Gen 徽章；插画 流行 / 美学 / 创意 + 诗意副文）。

`main.xml` — 主窗业务页（约 600 行）：

- **资源 `@ID_nav1`（默认选中）**：顶部分段 radio —— 验证界面（默认，有 listView 卡片网格）/ 盒子界面 → 「研发中，敬请期待~」+ `@no_data.png` / 暂未启用 · 资源使用说明 → `show=false`（勿画进正式 UI）。列表项约 290×224。

- **资源交互（合并）`@ID_nav4`**：向导式：页面1 选择 → 页面2 配置 + 日志。左说明彩条/步骤 + 灰底输入 + 态按钮 `btn_1..4` + 黑底主 CTA。

- **皮肤 `@ID_nav5`**：选择主题 + 授权路径 + 操作记录；顶说明可用 `@bg_sk.png`。

- **更新器 `@ID_nav7`**：选目录 → 模板 listView（`up_tmp_template` / `_sel`）→ 配置 → 侧栏日志；打包进度用 `UP_progress_page`。

- **排行榜 `@ID_nav3`**：顶分段 等级榜（默认）/ 宠物榜 / 积分榜 / 解锁榜 / 兑换券榜 +「成长值明细」→ `rak_detail`；Top3 异形大卡（`@ID_排名_徽标_第一/二/三`）；`listBoxUI`（模板 `raking1~5`）；底「我的排名」条。**与 humbox 不同：此处默认是「等级榜」，不是「V力值榜」。**

- **占位页（研发中）**：`@ID_nav2` 软件市场 · `@ID_nav6` 下载管理 · `@ID_nav8` 安装器 · `@ID_nav1_子页面_2` 盒子界面 —— 内容均为「研发中，敬请期待~」+ `@no_data.png`。

- **我的信息覆盖页**：Hi / 昵称 / 返回；等级卡 + 积分卡 + 已解锁 + 微信/QQ 绑定；背景 `@slf_bg.png`。

- **用户条（右侧顶下）**：VIP 徽标+进度 `@ID_用户信息_等级徽标`(v1) · `@ID_用户信息_等级成长进度`；用户名 `@ID_用户信息_用户名`「用户的名称」；宠物「宠物」+ `@ID_个人信息_宠物名称`「宠物名称」+ 等级；积分 `@ID_用户信息_积分`「- - 」；解锁 `@ID_用户信息_解锁` +「个」；兑换券 `@ID_用户信息_兑换券` +「张」；刷新 `@ID_用户信息_刷新按钮` tip「刷新数据」。

模态窗：`set.xml` — 750×480 · HUMSetting：左 w≈160「设置」radio 常规（默认）/ 调试功能 / 启动设置 / 关于我们；右 `:1` 标题 `@ID_设置_页面标题` + close；常规 开机自启动 · 最小化/前台展示(禁用) · 优化资源占用 · 禁用系统缩放 · 开启程序关闭提示；调试 开启皮肤调试 · 更新器/安装器预览(禁用)；启动 开启更新提醒；关于 未闻花名UI设计 · QQ · Bate 0.1 ·「点我加入官方QQ群」。窗背景 `@set_wng.png`。

`about.xml` — 520×440：关于我们卡片 logo +「未闻花名UI设计」· 技术支持 QQ · 版本 · 反馈按钮 ·「点我加入官方QQ群」· 版权。

`msg.xml` — 600×276：close · info.svg · 标题 · 只读多行正文 · 取消(可隐)/确认。

`fb.xml` / `qr_*`：fb 问题反馈 & 加群（QQ / 群 / 公众号复制）；qr_group 群号 **274320516** + `@gd_qr.png`；qr_qq **936599025** + `@qq.png`。

`rak_detail.xml` — 440×542：「等级成长值明细」说明 + V1–V10 与成长值区间两列表。

`UI_preview.xml` — 1920×1080：暗色半透明舞台；顶 资源名 | 返回；中 预览大图 | 说明；底 作者 / 获取方式 / 编号+复制 |「合并」「详细」。

**资源卡模板 `UI_template_1~4`** —— 统一 **290×222**：封面 266×164（图 + `UI_item_mask`），角标 `name4`，底条 `name1` 标题 + `name2` 副信息；底栏 类型徽章 + ID(`name3`) +「复制编号」。模板 1 积分兑换（深色角标）· 2 会员专享（橙角标）· 3 V8专享（暖色角标字 `#FFFFDCC1`）· 4 限时免费（浅角标）。绑定：`name1` 标题 · `name2` 副文 · `name3` 编号 · `name4` 角标 · `name5` 封面。

**排行模板 `raking1~5`** —— 行高 **66**，横向 `排名(name1)` | `昵称(name2)` | 图标 | `数值(name3)` | 单位。单位字：1 等级「级」· 2 积分「分」· 3 解锁「（解锁）」· 4 兑换券「张」· 5 宠物「级」。

**更新器模板 / 通知 / 进度**：`up_tmp_template` = 预览图 + 居中序号胶囊；`up_tmp_template_sel` = 选中描边 + 勾选 `@up_ic_09` + 底名称；`UP_progress_page` = 「正在打包…」+ 进度条 + 百分比；`inner_notify` = 绿勾 + 标题/正文 + 关闭。

**`flowing.xml`**：32×32 按钮，`@flow_ic1/2`，tooltip「显示未闻花名平台」，窗 topmost 半透明圆角。

### 3.5 hum 文案 / bindEle / 版权（06 §E）

| 左侧导航文案 | bindEle | 备注 |
|------|---------|------|
| 资源 | `@ID_nav1` | **默认选中** |
| 资源交互 | `@ID_nav4` | 按钮另有 id=`@ID_导航_合并` |
| 皮肤 | `@ID_nav5` | |
| 更新器 | `@ID_nav7` | |
| 安装器 | `@ID_nav8` | 内容多为占位 |
| 排行榜 | `@ID_nav3` | |
| 软件市场 | `@ID_nav2` | **「研发中，敬请期待~」** |
| 下载管理 | `@ID_nav6` | **「研发中，敬请期待~」** |
| 关于&反馈 | `@ID_分享与反馈` | 非 bindEle 页 |

资源子导航：验证界面 `@ID_nav1_子页面_1`（默认 · 有 listView）· 盒子界面 `@ID_nav1_子页面_2`（**研发中占位**）· 暂未启用 `@ID_nav1_子页面_3`（show=false）· 资源使用说明 `@ID_nav1_子页面_4`（show=false）。

排行榜子导航：等级榜（默认）· 宠物榜 · 积分榜 · 解锁榜 · 兑换券榜 · 另有「成长值明细」。

用户条 id → 默认 content：`@ID_用户信息_用户名`「用户的名称」· `@ID_个人信息_宠物名称`「宠物名称」· `@ID_用户信息_积分`「`- - `」· `@ID_用户信息_解锁` / 兑换券「` - `」· 徽标「v1」。

`set.xml` 开关文案：常规 = 开机自启动 · 最小化展示/前台展示（禁用）· 优化资源占用 · 禁用系统缩放 · 开启程序关闭提示；调试 = 开启皮肤调试 · 开启更新器预览（禁用）· 开启安装器预览（禁用）；启动 = 开启更新提醒；关于 = 未闻花名UI设计 · QQ · Bate 0.1 ·「点我加入官方QQ群」。

版权串（原文拼写，勿「修正」）：`Copyright © HUMUI 未闻花名. All Reghts Resrved.`

## 4. humbox 文案 / name / @ID_ 精校（06 §A–D）

layoutPanel 设计尺寸例外（多数内容页 `widthT=1024`）：home 1024×600；about 1024×**1100**；myinfo 1024×**1000**；updater_details **400**×420；mydata **500**×500；layoutFrame / loading / rk_total_rk = （空）。

**登录 `login.xml` 控件 ID** —— id → 类型 → 文案/tips：9 elementUI 品牌图占位（动态图槽）· 1 editUI tips「输入你的账号」caret `#BBF327` 圆角 6 · 2 editUI tips「输入你的密码」password · 3 button check 密码显隐（eyes_hd/sh）· 5 button check「我已阅读并同意」· 8 textLink「《用户协议》」hover `#c5f35f` · 4 button「登录」字色 `#21241f` · 7 textLink「联系客服」· 6 textLink「注册账号」· — shapeText「登录遇到问题？」「没有账号？」

**主 Tab / 资源 / 皮肤 / 交互**

主窗顶栏（main.xml）：文案 首页 / 资源 / 皮肤 / 交互（radio `groupID=0`；首页默认 check）；toolTip 返回[home] · 快捷键[1~4] · 我的信息[5] · 菜单[6] · 帮助[7] · 窗控[8][9][0]。

资源页子导航显示文案 → XML bindEle（注意）：皮肤主题 `@ID_皮肤_自定义加载` · 更新器 `@ID_皮肤_一键加载`（与下列共用，疑为设计器遗留）· 验证登录 `@ID_皮肤_一键加载` · 安装器 `@ID_皮肤_一键加载`。右上文案「出现任何问题，请随时与我们联系反馈」；内容槽 `name="资源_布局"`。

**AI 注意**：res 子 Tab 的 bindEle 与 skin 页 ID 撞名，画界面按**可见文案**即可，勿依赖 bindEle 语义。

皮肤页（skin.xml）子 Tab → bindEle / 面板 id → 主 CTA：自定义加载 `@ID_皮肤_自定义加载`「确认皮肤并授权」· 一键加载 `@ID_皮肤_一键加载`「一键授权皮肤」。表单标签：授权皮肤* / 对接程序* / 保存位置 / 程序位数* / 算法类型*；右侧栏标题「使用说明」· 列头「类型｜内容｜操作」。

交互页（Interaction.xml）子 Tab → 面板 id → 主 CTA / 关键钮：更新器交互 `@ID_更新器交互`「解析更新模板」→「打包数据」「生成配置」「确认生成更新器」「上一步」· 验证交互 `@ID_验证交互`（默认显示）「解析验证模板」· 安装器交互 `@ID_安装器交互`（同构，多禁用态）。

**设置 / 帮助 / 榜 / 名片**

`setting.xml`（右侧浅色抽屉）name → 文案：`set_01` toolTip「隐藏设置页面」· `set_02` 系统设置 · `set_03` 加入群聊 · `set_04` 关于我们 · `set_05` 更新检查 · `set_06` 查看平台用法 · `set_07` 充值 & 赞助 · `set_08` 未闻花名平台 v2.0。辅助文「若文档无法取得帮助，可加入群聊、联系未闻花名进行协助。」

`settingWnd.xml`（完整设置）左导航 **通用 / SDK / 外观 / 系统**：通用 = 开机启动 · 背景音乐 · 关闭程序时弹出提示 · 显示日志（隐藏后可通过 皮肤\交互 板块右上角图标显示）；SDK = 开启更新 · 开启资源更新检查 · 开启平台SDK更新检查 · 开启更新提示窗口（右下角展示）；外观主题（节选）= 云野仙踪（默认）· 森澜祈光 · 森澜雾境 · 苏暖暖Ⅰ · 苏暖暖Ⅱ · 月度摇光 · …（缩略 138×110）；系统 = 含「跟随系统音量…」「模糊模拟效果…」「优化资源占用…」等。

`helpWnd.xml`（200×388）菜单 id → 文案：1 帮助文档 · 2 皮肤说明 · 3 更新器说明 · 4 验证说明 · 5 安装器说明（**enable=false**）· 6 宠物系统 · 7 插件说明（**enable=false**）· 8 设为壁纸 · 9 联系我们。

排行榜类型（`rk_total_rk.xml`）：`V力值榜`（默认）· `宠物榜` · `积分榜` · `解锁榜` · `兑换券榜`（name: `rk_list_01~05`）。

`mine.xml` 名片：用户名默认「未闻花名UI」· V 标「V1」· 进度说明含「V力等级…」· VIP 条 +「续费」·「查看我的信息」· toolTip「查看V力值详细」。

`preview.xml` id → 文案/tip：3 顶条「资源的名称」+ 钮「使用」· 1 主卡「资源预览的标题」· 4「作者」tip「点击复制作者QQ」· 5「类型」· 6「编号」tip「复制编号」· 8「兑换」tip「兑换并解锁…」· 7 tip「隐藏预览详细」。

`VIP.xml`：标题层「未闻花名平台VIP」· 用户「未闻花名」· 有效期占位 · 权益三行 个性装扮 / 专属资源 / 随心畅享 · 套餐 自定义月数 · **1个月（默认）** · 2/3/6/12个月（积分价 **100/200/300/600/1200**）·「开通会员」字色 `#653D00` ·「《会员服务协议》」。

`msg.xml`：标题 id=1「系统通知」· 正文 id=3「这是一条系统通知消息。」·「取消」id=7 ·「确认」id=4。

**易错点（06 §F）**

1. humbox **res** 子 Tab 文案是「皮肤主题/更新器/验证登录/安装器」，不是 skin 页的「自定义/一键」。

2. humbox **skin** CTA 是「确认皮肤并授权 / 一键授权皮肤」；**Interaction** CTA 是「解析更新/验证模板」等。

3. hum 占位页不止安装器：软件市场、下载管理、资源-盒子界面也是「研发中」。

4. hum 排行默认「等级榜」；humbox 排行默认「V力值榜」——文案不要混用。

5. `layoutFrame`/`loading`/`rk_total_rk` 无 1024 宽，勿强行套首页 padding。

6. 主强调色：humbox 登录链接 hover 是 `#c5f35f`（小写也可）；VIP 开通钮字是 **金棕** `#653D00`，不是黄绿。

## 5. 产品页画法（跨 hum/humbox，05）

- 第一屏构图 · humbox 首页：① 一张 1168×670 深色窗（轻投影），**无**左永久侧栏 ② 顶栏 80：LOGO → 回退 → Tab「首页｜资源｜皮肤｜交互」（选中 **2px 黄绿条**）→ 头像 → 窗控 ③ 内容约 1024 宽：上横滑卡 + 下左横幅 + 右 2×2 ④ 第一屏只放：壳 + 顶栏 + 首页内容。

- 第一屏构图 · hum 资源页：① 一张 1180×720 浅色圆角窗 ② 左 180：LOGO + MENU/SOFT +「关于&反馈」③ 右：图标栏 → 用户 chip → 分段 + 卡片网格 ④ 选中导航：浅暖色底，不是黄绿下划线。

- 页面模式速查 · humbox：工具页=顶 pill radio+左右栏 · 排行=左我的排名+中表 · 登录=竖卡 · 预览=暗罩+右侧竖钮 · VIP=暗金横卡 · 设置窗=左 140 导航 · 名片=290×243。

- 页面模式速查 · hum：资源=下划线分段+网格 · 排行=Top3+列表 · 工具向导=左说明+黑 CTA+日志 · 登录 Pro/Gen 左右镜像 · 设置=左 160 · 预览=全屏暗舞台。

- 设计禁区（只管「画得像不像」）：① 禁止 hum↔humbox 导航/配色混搭（除非画 humbox `settingWnd`）② 禁止整站紫渐变 / 奶油纸 / 报纸密排 ③ 卡圆角 humbox **2–6**、hum **6–12**，勿大圆角卡片墙 ④ 禁止第一屏塞统计条、日程、地址、多段营销 ⑤ 禁止把占位页画成完整功能（软件市场/下载管理等）⑥ 去掉导航后仍应认出「未闻花名 / HUMUI」⑦ 榜名单 hum「等级榜」、humbox「V力值榜」⑧ VIP「开通会员」字色金棕 `#653D00`，勿黄绿底 ⑨ 禁止臆造文案 → §4。工程向禁区（系统标题栏、空 shaped、98 禁用、`/` 后属性、白 logo、代码盖壳）→ `interface-xml.md` §6/§7。

- 配色速记 · humbox：近黑底 · 强调 `#C5F35F` · CTA 字 `#21241F` · 正文白 · VIP `#653D00`；hum：浅壳 · 主字 `#181D27` · 次字 `#9B9EA2` · Pro `#FD687E` · Gen `#CA8BFF` · 链接 `#0079f4`。

- 动效（每屏 2–3）：humbox = Tab 下划线；卡 hover；CTA 轻按。hum = 导航选中 fade；VIP 扫光；悬浮球呼吸。

- 提示词骨架：

```text
根据 md/界面md 画界面。
目标项目：【hum | humbox】
目标页面：【…】
必读：05 + 06 + 对应 overview/pages
约束：不混项目；文案=06；第一屏无统计条；品牌可见
输出：高保真静态稿
```

- 阅读分流：画 humbox = 05 → 01 → 02 → 06 §A–D；画 hum = 05 → 03 → 04 → 06 §E；落地工具窗 = 09 → 07（翻车时）；产品窗壳表 = 08。源码 `Downloads\hum` · `Downloads\humbox`。

> 源注记：`界面md/README.md` **不存在**（源 `xc-代码/skill.md` 已声明），不要生成指向它的链接。

## 6. 常见任务工作流

- **任务 1 新增图片/字体资源**：① 文件放入 `资源文件/`（SVG 用 `style="default" svgAlpha="255" svgRotateCenter="1"`；9宫格 PNG 用 `style="image9" rect9="l,t,r,b"`）② 在 `资源文件/resource.res` 的 `<type_image>`（或 `<type_font>`）照同类条目抄一行注册 ③ 布局里以 `4(@名)`（bkInfoM 图片段）或 `image="@名"`（shapePicture）引用 ④ 字体 token 命名 `字号 + b(粗) + _yh(雅黑)/_vv/_num(数字字体)`。

- **任务 2 新建窗口**：① 新建 `布局文件/<名>.xml`，固定开头 `<?xml version="1.0" encoding="UTF-8"?>` + `<!--炫彩界面库-窗口布局文件-->` + `<head />` ② 根元素 `<windowUI className="唯一名" ...>`（className 是宿主加载名；弹窗加 `windowType="modalWindow" center="true"`）③ 参照同类型现有窗口抄骨架（msg.xml=消息框、input.xml=输入框、sponsor.xml=带文案弹窗）④ 窗口视觉基线：暗色圆角 + 8px 阴影（`shadowSize="8" shadowDepth="75"`），关闭按钮 `buttonType="close"` 三态换图。

- **任务 3 给主窗口加导航页**：① 新建面板 `布局文件/<页名>.xml`（根 `<layoutPanel>`，首行注释 `<!--炫彩界面库-布局面板文件-->`）② main.xml 标题栏导航区（`groupID="0"` 的四个单选）加一个 `buttonType="radio" groupID="0"` 按钮，样式**照抄相邻导航按钮的 bkInfoM**，只改文字段 ③ 面板由宿主注入 main_body——布局文件只声明，不加宿主代码 ④ 页内二级导航：单选 `groupID="N"`(顺延新号) + `bindEle="@ID_新符号"`，resource.res type_id 注册新 ID（**从 125 顺延**），被控面板 `id="@ID_新符号"` + `showT="false"`。

- **任务 4 改样式（bkInfoM）**：① **先读 `bkinfom-res.md`**——bkInfoM 无官方文档，语法全部从本项目反推 ② 优先在 `布局文件/` 全文搜索现成配方（垂直渐变搜 `24(2,90.00`、圆角4搜 `9(4,4,4,4)`、卡片底搜 `22(654311423)`），复制改参数 ③ 改颜色的唯一正确方式：有符号十进制 ↔ 无符号 ↔ `#AARRGGBB` ④ 同一样式出现 3 处以上时注册为命名样式（resource.res type_bkInfo）再 `bkInfoM="@名"` 引用。

- **任务 5 新增列表项模板**：① 按目标控件选根标签：listViewUI→`<xc_template_listView>`（含 listView_Group+listView_item）、listUI→`<xc_template_list>`（含 listHeader_item+list_item）、comboBoxUI→`<xc_template_listBox>` ② 数据字段用 `{binding field=name1}` 形式 ③ 抄最接近的现有模板改（资源卡片抄 res_item_temaplate_free.xml，下拉项抄 combobox_template.xml）。

**humbox 红线（只列本文件独有的两条；通用约束见[开发与验证规则](task-rules.md)）**

- **勾选不要吃系统灰底**：用 `buttonType="check"` + `transparent="true"` + `@复选框`（命名样式；`98:272/288/320` 未选 / `128/144/192` 已选，映射 `check_off` / `check_off_h` / `check_on` 三张 SVG），并用 `offsetXY="22,0"` 把文字让到方框右侧——不要只写 `style="check"`。

- **已知悬空引用别扩散**：`flow_ic1.svg`、`home_btn3_icon_01.svg` 在布局中被引用但文件不存在（运行时不显示），不要照抄进新文件。

**修改前的标准动作**：① 在文件地图（§2.7）定位目标文件 ② Read 目标文件及周边关联文件（上游容器/下游模板）③ 涉及 bkInfoM → 先读 `bkinfom-res.md`；涉及布局属性 → 读 `interface-xml.md` §2 ④ 改动保持最小：抄现有配方改参数，不发明新模式 ⑤ 完成后全文搜索被改的 @资源名/@ID/name，确认无遗漏引用。

