# humbox 文件地图

全部布局/资源文件的分类索引与相互关系。**做任何修改前先在此定位文件**，再读原文件。

路径基准：`I:\炫彩ide\UI样式\humbox\`（下文 `布局文件/` 即其子目录）。

## 1. 窗口布局（17 个，根 `<windowUI>`，宿主按 className 加载）

| 文件 | className | 尺寸 | 用途 |
|---|---|---|---|
| main.xml | humbox | 1168x670 | 主窗口：标题栏导航（首页/资源/皮肤/交互）+ main_body 页面槽 |
| login.xml | humbox | 450x650 | 登录窗（shaped 异形）：账号/密码、协议复选、注册/客服链接 |
| msg.xml | MdMsg | 500x320 | 系统通知消息框（modalWindow） |
| UsrTA.xml | MdNotf | 660x490 | 用户协议弹窗 |
| mine.xml | mineCard | 290x243 | 用户信息卡片（mine_bg.png 底） |
| VIP.xml | vipAc | 702x362 | VIP 开通弹窗（金紫色调、折扣角标、有效期） |
| VIP_agrmt.xml | vAgrmt | 640x220 | VIP 会员协议（三条会员规则 + 确认） |
| preview.xml | humboxPv | 1572x850 | 资源预览大窗（使用按钮、资源预览标题） |
| input.xml | humboInput | 480x507 | 通用输入对话框（请输入内容、多行编辑） |
| settingWnd.xml | humSetting | 680x520 | 设置弹窗：左侧图标单选导航（通用/SDK/外观…六项） |
| sdk.xml | sdkhp | 800x480 | 未闻花名引擎SDK 日志窗（清空记录、横竖布局切换） |
| SDKupdate.xml | SDKUpd | 650x480 | SDK 环境更新弹窗 |
| updater.xml | humboxUpd | 336x432 | 静默更新小窗（topmost、查看详细） |
| vol_bg.xml | volAhpl | 880x500 | 火山MFC窗口组件快速处理弹窗 |
| helpWnd.xml | humHpr | 200x388 | 帮助菜单浮窗（帮助文档/皮肤说明/更新器说明/验证说明…） |
| sponsor.xml | SponsorWnd | 716x376 | 赞助弹窗（QQ 936599025、10 V力值+10积分/元） |
| flowing.xml | flowUI | 42x40 | 桌面悬浮球（toolTip: 显示未闻花名平台） |

另有根目录 `Test.xml`（7KB，1936x1226）：设计器实验草稿，非正式界面，**不要当风格参考**。

## 2. 布局面板（18 个，根 `<layoutPanel>`）

**主页面板**（注入 main_body，由主导航切换）：
| 文件 | 用途 |
|---|---|
| home.xml | 首页：横向滚动卡片流（home_01 容器、渐变卡片 215x292、敬请期待占位）+ 底部功能按钮区 |
| res.xml | 资源页：顶部单选导航（皮肤主题/更新器/验证登录/安装器，groupID=2，bindEle 切换）+ 资源_布局容器 |
| skin.xml | 皮肤页（17.6KB 最复杂表单页）：自定义加载/一键加载双子面板（groupID=3）、授权皮肤组合框、对接程序、保存位置、程序位数、算法类型、火山自动主题色、SDK 日志按钮 |
| Interaction.xml | 交互页（25KB 最大）：更新器/验证/安装器三模块配置，三层嵌套 bindEle 面板（→程序配置→配置详细），模板选择、更新目录、打包数据、生成配置等 |

**二级面板**（宿主按 name 挂载/切换）：
| 文件 | 用途 |
|---|---|
| about.xml | 关于页 |
| avatar.xml | 头像选择 |
| mine.xml 对应面板：myinfo.xml | 个人资料编辑（11.3KB，头像框选择+资料表单） |
| mydata.xml | 我的数据 |
| Vv.xml | V力值等级页（Vvmask 蒙版、等级 1 展示） |
| res_page.xml | 资源子页 |
| setting.xml | 设置内容区（settingWnd 左导航切换） |
| raking.xml | 排行榜主页（我的排名、成长值/排名列） |
| rk_total_rk.xml | 总排行榜 |
| layoutFrame.xml | 通用更新帧模板（_up_title/_up_time/_up_content/_up_update/_up_prog/_up_task_text/_up_task_prec 七个宿主填充槽） |
| updater_details.xml | 更新详情 |
| progress.xml | 进行中面板（进度条：打包XXX） |
| dropfile.xml | 拖入文件面板（拖入文件到窗口内 / 按下 ESC 取消） |
| loading.xml | 加载占位（300x300） |

## 3. 列表项模板（21 个）

**listView 模板（6 个，`<xc_template_listView>`，资源卡片 318x294，字段：缩略图/name1）**：
`res_item_temaplate_free / _member / _point / _private / _unlocked / _VIP` —— 免费资源、会员、积分、私有、已解锁、VIP 资源卡片。卡片结构：缩略图(278x180 圆角6) + 标题(未闻花名验证001名称) + 查看详细按钮 + 限免徽章 + 未闻花名标识 + QQ 联系方式。

**list 模板（14 个，`<xc_template_list>`）**：
- 排行榜 12 个：`raking_{first,second,third,other}_{pet,point,v}.xml`（前三名×3 变体 + 其他名次×3 变体；pet=宠物/point=积分/v=V力值；绑定字段 排名/用户名/头像）
- `sdk_template.xml`：SDK 日志行（字段 序号）
- `updater_list_itemTemp.xml`：更新器列表行（字段 name1）

**listBox 模板（1 个，`<xc_template_listBox>`）**：
`combobox_template.xml`：下拉框项（字段 name1，@10 白字左对齐 padding 16）

## 4. resource.res 注册内容速查

### type_id（15 个符号 ID）
```
110 ID_皮肤_一键加载          111 ID_皮肤_自定义加载
112 ID_皮肤_自定义加载_使用说明  113 ID_皮肤_自定义加载_程序配置
114 ID_皮肤_一键加载_使用说明   115 ID_皮肤_一键加载_程序配置
116 ID_验证交互_程序配置       117 ID_验证交互_使用说明
118 ID_更新器交互_程序配置     119 ID_更新器交互_使用说明
120 ID_验证交互              121 ID_更新器交互
122 ID_安装器交互            123 ID_皮肤_一键加载_程序配置_配置详细
124 ID_更新器交互_程序配置_配置详细
```
新 ID 从 125 顺延。

### type_font（23 个字体 token）
`9 9b 9_yh 9_num 10 10b 10_yh 10b_yh 11 11b 12 12_vv 12b 13 13_num 13_vv 13_yh 13b 15b 16b 18b 26b 8_yh`

### type_bkInfo（18 个命名样式）
| 名称 | 用途 |
|---|---|
| 滚动条 / 滚动条_白色 | 滚动条滑块三态 |
| 复选框 | 复选框全态（含 ckd.svg 对勾） |
| 头像{0-3}_主页面 | 32x32 头像（0=描边 1=五角星 2=VIP金 3=模块紫） |
| 头像{0-3}_个人信息 | 120x120 头像 |
| 头像框{0-3}_编辑头像 | 80x80 可选头像框（含选中态 sel_av.svg） |
| 头像预览{0-3} | 160x160 头像预览 |

### type_image（约 230 条）
图片清单与 资源文件/ 目录一一对应（除 architecture.md 第 6 节列出的 4 处不一致）。常用族：`close{1,2,3}.svg`、`navbtn_icon_{skin,update,login,install}_{01,02,03}.svg`、`combobox_icon_{01,02,03}.svg`、`help_icon_*.svg`、`vip_icon_{01..05}.svg`、`first/second/third_icon_{01..06}.svg`、`Vv_s_v{1..10}.png/v{01..09}.svg`、`头像框{1,2,3}_{32,80,120,160}x{32,80,120,160}_{00..05}.{png,svg}`、`login_sd.png`/`xy_sd.png`/`updater_wnd_sd.png`（9-patch 窗口边框）。

## 5. 依赖关系图

```
resource.res ──注册──> 全部图片/字体/符号ID/命名样式（布局以 @名 引用）

main.xml (humbox)
 ├─ main_body 槽位 <── home.xml / res.xml / skin.xml / Interaction.xml（主导航 groupID=0 切换）
 │    ├─ res.xml ──bindEle──> 资源子面板（@ID_* 系）+ res_item_temaplate_*.xml 卡片 + combobox_template.xml
 │    ├─ skin.xml ──bindEle──> @ID_皮肤_自定义加载 / @ID_皮肤_一键加载 两个子面板
 │    ├─ Interaction.xml ──bindEle──> @ID_更新器交互 / @ID_验证交互 / @ID_安装器交互（各自再嵌套_使用说明/_程序配置/_配置详细）
 │    │    └─ 关联窗口: sdk.xml(SDKUpd) / vol_bg.xml(volAhpl 火山MFC)
 │    └─ home.xml ──横滚卡片──> home_item1_bg.png 等资源
 ├─ 弹窗族: login.xml(humbox) / msg.xml(MdMsg) / mine.xml(mineCard) / myinfo.xml→avatar.xml
 │   / VIP.xml(vipAc)→VIP_agrmt.xml(vAgrmt) / settingWnd.xml(humSetting)→setting.xml
 │   / preview.xml(humboxPv) / input.xml(humboInput) / UsrTA.xml(MdNotf) / helpWnd.xml(humHpr)
 │   / sponsor.xml(SponsorWnd) / Vv.xml 面板 / sdk.xml(sdkhp) / SDKupdate.xml(SDKUpd)
 ├─ 更新器链: updater.xml(humboxUpd) ──> layoutFrame.xml(_up_* 槽) / updater_details.xml + updater_list_itemTemp.xml
 ├─ 工具面板: progress.xml / dropfile.xml / loading.xml
 ├─ 排行榜链: raking.xml ──> rk_total_rk.xml ──> raking_{first,second,third,other}_{pet,point,v}.xml
 └─ 桌面悬浮: flowing.xml(flowUI)

Test.xml = 独立草稿（引用 Vv_* 资产实验，与上述链无正式关联）
```

## 6. 找文件的最快方式

| 需求 | 去处 |
|---|---|
| 改主界面标题栏/导航 | main.xml |
| 改某页面内容 | 第 2 节主页面板四文件 |
| 改弹窗 | 第 1 节按 className 找 |
| 改列表行/卡片外观 | 第 3 节模板 |
| 加图片/字体/ID/复用样式 | 资源文件/resource.res 对应 type_ 节 |
| 查某资源是否被用 | 在 布局文件/ 全文搜 `@资源名` |
| 查某元素被宿主怎么用 | 全文搜元素 name（如 皮肤_自定义加载_对接程序_编辑框） |
