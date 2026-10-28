# -*- coding: utf-8 -*-
"""
微星主板 BIOS 下载工具  MSI Motherboard BIOS Downloader
========================================================
功能：
  1. 主板目录浏览：从微星官网产品接口自动拉取全部在售主板（约 500 款，含中国站特供补录），
     左侧目录树按「Intel 主板 / AMD 主板」两大平台归类，再按芯片组（Z890/X870E/B760…）分组；
     顶部「型号定位 / 搜索」输入关键字可从目录定位，目录无结果时自动打开官网搜索（含已停售型号）。
     目录首次联网加载后写入本地缓存（msi_mb_catalog.json），之后可离线浏览；后台按设置间隔自动刷新。
  2. 选中型号即从官网 Support 数据接口获取该主板全部 BIOS 版本列表（官方 JSON API），
     显示 版本 / 发布日期 / 大小 / 更新说明，支持下载任意版本（进度条 / 取消 / SHA-256 校验）。
  3. 数据来源：https://www.msi.com 与 https://www.msi.cn 双站（全球站无数据的特供型号自动回退中国站）
  4. 设置（v2.1.0+）：目录自动刷新间隔、显示平台 / 芯片组范围可自定义，支持手动「立即更新目录」，
     保存后立即生效，无需重启（设置文件 msi_bios_checker.cfg）。
  5. v2.2.0：恢复经典深色布局 —— 左侧主板目录树 + 顶部搜索行 + 刷新目录按钮。
  6. v2.3.3：DNS 自愈 —— 运营商/路由器递归 DNS 偶发无法解析官网域名（curl error 6/28）时，
     自动改用 DoH（DNS over HTTPS：阿里 223.5.5.5 / 腾讯 DNSPod，IP 直连不依赖系统 DNS）重试，
     避免「目录更新失败」；仍失败时提示可读中文。
  8. v2.1.1：目录树 #0 列宽改为按目录数据实测自适应（写死 300px 时 12 款长型号名
     被裁，如 "MEG X870E ACE MAX DRACO EPIC EDITION" 只显示到 "…EPIC E"）。
  7. v2.3.4：左侧主板目录树缩进收紧（indent=16），消除三级层级前的空旷留白。
  8. v2.3.5：主操作按钮白字锐化 —— 字号 -17→-18px + 红底加深，ClearType 白字更实；
     代码稳健性（目录未就绪/设置损坏不崩溃、查询失败显示占位、队列消息不丢）。
  9. v2.3.6：右上角两个按钮视觉分组 ——「打开官网支持页」改为 Link 风格（蓝色文字 + ↗ 箭头，
     背景与主板卡同色），「打开目录」改为 Ghost 边框风格（深灰底+细边），与主红按钮
     「下载选中版本」形成「红主操作 / 灰边次操作 / 蓝链外引」3 层视觉差异。
 10. v2.3.7：主操作按钮与目录树三处 UI 对齐修复 ——
     ①「下载选中版本」从 ttk.Button 改 tk.Button（沿用设置窗「立即更新目录」红主配色，
       padx=18/pady=8），彻底去掉 vista 主题 ttk.Button 默认附加的 ■ 装饰噪音；
     ② 左侧主板目录树 #0 列宽 200→300px，Z890/MAG 长主板名不再被截断为 "...WI"；
     ③ 主板目录树缩进 16→10px，chipset 下的 board 型号再向前缩 12px 紧凑显示。
     （对应状态切换统一改 config(state=tk.DISABLED/NORMAL, bg=...)）
 11. v2.4.0：UI/UX 全量升级 ——
     ① 布局重构：右侧 BIOS 区改为固定宿主容器（list_holder），列表重新 pack 时
       不会跑到下载区下方（修复旧实现的隐 bug）；下载区从一行挤 5 个控件改为
       「保存目录行 + 操作按钮行」两行分组；状态栏右侧常驻「数据源 + 版本号」；
       主板标题副行加数据源徽章；窗口最小尺寸调到 1100×760 容纳新分组。
     ② 交互：新增搜索框（实时过滤型号/芯片组，140ms 防抖，自动展开命中芯片组，
       无结果抖动 + 弹出「去官网搜索」覆盖已停售型号）；列表行 hover 高亮（普通
       行 / 最新行 两套配色）；保存目录路径单击即打开；右键菜单（复制版本号 /
       复制下载链接 / 打开官网）；快捷键 Ctrl+F 聚焦搜索 / Esc 清空 / F5 立即
       刷新目录 / Enter 触发下载；左栏加 ↻ 立即刷新按钮（不再必须进设置）；
       空状态三态（未选型号 / 查询中 / 无数据）；下载中显示速度 + 剩余时间。
     ③ 动效（Anim 统一帧调度器，空闲自动停表 —— 零 CPU 占用）：
       列表切换型号淡入（前景/背景颜色 200ms 缓出渐显）；
       进度条平滑补间（300ms 缓动逼近，不再整数跳变）；
       下载完成红→绿脉冲（460ms）+ 状态栏文字闪烁（900ms）；
       按钮 / 链接 hover 背景 / 前景 140ms 渐变；
       搜索无结果输入框左右轻抖（280ms 衰减）；
       查询中空状态图标颜色脉冲 + 文字点动画。
     ④ 最新版本号前加 ★ 前缀 —— Treeview 的 selected 状态会覆盖 tag 颜色，
       自动选中最新的那行时 tag 的绿底会被顶替成选中暗红，前缀字符让「最新」在
       任何选中态下都一目了然（复制菜单用 clean_version 拿原始值，不受影响）。
     ⑤ 结构性细节：搜索框用 tk.Entry（确定性 fg/bg），独立 Anim 调度器 +
       搜索/快捷键/hover/右键/结果横幅/加载态等方法块。
12. v2.0.0：全量代码审核与优化（版本号重置为 V2.0 主线）——
     ① 修复「下载选中版本」永久禁用：查询成功分支漏发 busy=False，选完型号后
       主按钮一直停在 disabled 暗红（严重功能 bug）。
     ② 修复结果横幅从不显示：_toast 位于 grid 布局的右栏却用 pack 显示，
       TclError 被 except 吞掉；改为 grid / grid_remove。
     ③ 补齐「取消下载」入口：dl_cancel 与下载线程本就支持取消，但界面没有按钮，
       与文档承诺不符 —— 下载中在操作行显示「取消下载」（Ghost 风格），完成隐藏。
     ④ 移除死代码：从未被调用的 get_tabs/API_TABS、永不生效的
       _enable_dpi_awareness（ctypes 作用域错误 + 用错 DLL）、未使用的
       _btok/_status_kind/_fade_p/_last_done_path 与 4 个未用配色常量、未用的 TEntry 样式。
     ⑤ 健壮性：下载文件名做安全清洗（防路径穿越 / 非法字符）；_selected_item 改用
       iid→item 映射（不再靠版本号字符串反查，避免「—」重复匹配到错行）；
       _log 超过 1MB 自动轮转；打开目录加异常保护。
     ⑥ 流程优化：消息轮询间隔自适应（空闲 160ms / 有任务 60ms）；源码运行时
       设置窗口图标；下载复位时先取消进度条补间，避免与上一次动画互相覆盖。
 13. v2.1.0：真·高 DPI —— PerMonitorV2 感知 + 全量像素度量按真实 DPI 缩放 ——
     ① 旧版从未声明 DPI 感知（v2.0.0 移除的 _enable_dpi_awareness 因 ctypes 作用域
       错误从未生效），高缩放比（125%/150%/200%）或高分屏上整窗被系统位图拉伸发虚。
     ② _init_dpi() 在创建 Tk 之前声明感知（PMv2 → PerMonitor → System 逐级回退）；
       S(px) 把 96 DPI 设计基准换算为物理像素，95 处度量全量接入（含负值像素字号
       —— tk scaling 只作用于 pt 字号，字体改由 _rebuild_fonts() 按 DPI 重建）。
     ③ 窗口 / 设置窗 geometry 与 minsize 夹紧到屏幕工作区（高缩放比 + 小屏不超屏）；
       tk scaling 修正为 DPI/72；Tk 创建后按窗口所在显示器 GetDpiForWindow 二次校准；
       非 100% 缩放时状态栏版本号后显示「· DPI 150%」便于确认生效。
     ④ 100% 缩放下 S(px)==px，与 v2.0.0 渲染逐像素一致（3 场景 936000 像素零差异）。
 14. v2.2.2：进度行标签格预留改为按**真实上界文案实测**，修掉默认尺寸下的误降级 ——
     ① 缺陷：v2.2.0 把「完整进度文案」的标签格写死 46 字符（46×9px=414px），而完整文案
       真实最宽只有 374px；这条**估出来的**宽度还被当成降级阈值。默认 1200×780 在
       「目录加载完成、左栏由 360 扩到 417px」之后进度行掉到 699px < 728px，进度条被
       **永久**降级成短文案：看不到总量 / 速度 / 剩余时间，而窗口其实够宽。实机日志
       原文『进度文案压短（进度行 699px / 需要 728px）』。
     ② 修法：新增 PB_TXT_FULL / PB_TXT_SHORT 两条上界样例，阈值与标签格宽共用同一个
       实测像素宽（_pb_sample_px / _pb_label_chars / _pb_label_px），不再有估的宽度
       参与判定；PB_BAR_MIN 300→280（旧值是按 46 字符格的假宽度定的）。
     ③ 效果（100% DPI，实测）：1100 已加载 599px 仍压短（行为不变）；1200 已加载
       699px 由**压短 → 完整**；进度条本身同时变宽（1200 已加载 271→300px、
       1100 短文案 423→425px）。
     ④ 门禁：_opt_gui.py [7] 新增「默认 1200×780 + 目录已加载必须显示完整文案」断言。
 15. v2.3.0：UI 全面重设计（Apple 流体界面）+ 布局结构性重构 ——
     ① 动效引擎：新增解析解弹簧内核 Spring(ζ, response)（ω₀ = 2π/response），
        令牌 SPR_VALUE / SPR_ENTER / SPR_BANNER / SPR_PRESS / SPR_SHAKE /
        SPR_PULSE / SPR_EMPTY 分别对应「通用值过渡 / 内容入场 / 横幅出退场 /
        按钮按压回弹 / 无效操作回摆 / 完成脉冲 / 空状态入场」；静止判据用
        「位移 + 速度」双阈值（SPR_EPS_X / SPR_EPS_V），空闲自动停表（零 CPU）。
        接入 Windows「减弱动效」开关（SPI_GETCLIENTAREAANIMATION），
        关闭时全部弹簧直接落终值，不做动画。
     ② 视觉系统：窗口底 #1b1e24 -> #16181e（与卡片 C_CARD 拉开层次）；卡片去掉
        描边改纯色分层；品牌条改 2px 渐隐；进度条由 ttk.Progressbar 换成自绘
        PbarCanvas 胶囊条（圆头 + 平滑补间）；新增状态点脉冲 _dot_pulse 与
        状态栏闪烁 _status_flash。
     ③ 布局结构（本轮）：左右栏之间新增 10px 可拖拽分隔条（自建 tk.Frame +
        1px 中线 + hover 变色 + 双击复位 + 宽度持久化到 cfg.left_w）；
        左栏宽度改三级优先「用户拖拽值 > 布局区 0.30 比例跟随 > 型号名实测所需」，
        钳制区间 [SPLIT_MIN_LEFT, min(LEFT_MAX, 布局区 - 分隔条 - CAT_RIGHT_MIN)]；
        副标题（型号 slug）并入标题行、删掉独立副行；
        「保存目录行」并入「操作行」（目录路径 + 4 个按钮同一行）；
        列表行高 34 -> 32、按钮行高 56 -> 48、行距统一到 8-10px。
     ④ 收益（100% DPI 实测）：列表可视高 338 -> 407px（+20%），可视行数
        9.9 -> 12.7 行（+28%）；左栏宽度 1100/1200 -> 417、1400 -> 417、
        1600 -> 468、1920 -> 470，右栏 633 -> 733 -> 933 -> 1082 -> 1400
        单调增长不抖动；标题行四方竞争（标题 322 + slug 198 + 徽章 138 +
        按钮 167 = 825px）按「标题 > 数据源徽章 > 官网按钮 > slug」让路，
        1200 下 slug 主动让位、标题保持完整。
     ⑤ 顺带修掉的既有缺陷：_body_width() 返回的是**含 padding 的控件宽**，
        旧钳制公式漏减 BODY_PAD_X * 2 = 40px —— 旧版夹紧分支从未被触发过所以
        一直没现形，分隔条让用户第一次能拖到上限，右栏立刻掉到 580px <
        CAT_RIGHT_MIN(620) 保底。已抽 BODY_PAD_X 常量让 _left_limits 与
        _build_ui 共用同一个口径。
     ⑥ 门禁：新增 _p_v231_split.py（分隔条 6 组断言）、_p_v230_layout.py
        （布局体检）、_p_v230_pbsync.py（进度数据层）、_p_v230_pxbox.py
        （成品 PNG 像素反推）；_opt_boot_flow.py 三个断言按新规格重写
        （期望值由规格常量独立算出，不复用被测函数，避免同义反复）。
 16. v2.4.0：界面视觉焕新「石墨精工」（只改样式层，不动结构与尺寸公式）——
     ① 色彩语言：冷蓝灰 -> 中性石墨。27 个色令牌做色度中性化，19 个中性面的
        通道差 max(R,G,B)-min(R,G,B) 从 8-29 收到 4-15（中位 8-11）；明度阶梯
        重排为 L0 #17191b(24.72) / L1 #272a2e(41.65) / L2 #32363a(53.44)，
        底->面 16.9、面->浮 11.8（v2.3.1 基线 14.7 / 9.9，两级都超）。
        底色刻意不再压暗（v2.3.2 已实测底色进纯黑区会触发 ClearType 橙红色环），
        级差靠把面/浮提亮来挣。
     ② 红色预算：C_RED_HOT 从卡片小标题 Section.TLabel 与目录树 platform 行撤出
        （引用 3 -> 0）；目录树三级层级改由**纯明度**分层
        （C_TEXT 230 > 新增 C_CHIP 201 > C_SUB 174），不再色相与明度混用。
        红色只留在品牌条 / logo / 进度条 / 主按钮 / 输入框 focus / 失败状态点。
     ③ 读数等宽：新增 _mono_family()（优先 Cascadia Mono；与 _ui_font_family()
        同为「兜底 + 建窗后重算」，无 Tk root 时返回首选值且不写缓存）与
        FONT_MONO / MonoDim.TLabel / MonoSub.TLabel，落在目录更新时间戳、
        主板目录计数、状态栏右读数三处。**进度文案故意不用**：实测
        PB_TXT_FULL 在等宽下 374 -> 448px（+19.8%），会把 _fit_progress_text
        的压短阈值从 685px 顶到 757px，默认 1200 窗口（进度行 699px）会从
        「完整文案」变「压短文案」——那是行为变化，越界。
     ④ 顺带修掉 3 个既有对比度欠债（用基线回算证明是旧账不是新债）：
        C_DIM on C_CARD 4.11 -> 4.78；C_WATERMARK on C_CARD 2.54 -> 3.24
        （图形档 3:1）；C_DIM on C_STATUS_BG 4.27 -> 5.23；
        C_OK on C_OK_BG 4.30 -> 4.66。
     ⑤ 修掉既有缺陷「最新」行绿底从未渲染：该行 tags=("latest","row")，两个 tag
        都配置了 background，而 ttk::treeview 的规则是**先创建的 tag 优先**
        （与 tv.item(tags=[...]) 的书写顺序无关）—— row 先建，于是 C_CARD 一直
        盖住 C_GREEN_BG。把 latest 提到 row 之前创建即修复（应用级取色
        0 -> 17125 像素）。这是**既有缺陷**：v2.3.0 及更早的预览图里旧绿底
        同样 0 像素。另：tag_configure 对已存在 tag 是原地改值、不改变创建序，
        故 _apply_row_colors 里的书写顺序与优先级无关。
     ⑥ 动手前实测证伪两条路：ttk 的 lightcolor/darkcolor 对 alt 主题 TFrame
        无效（画的是机制自算的固定 +57 亮度跃升），"上受光/下背光"立体边路线
        不成立；本机 275 个字族中没有 MiSans / HarmonyOS Sans，界面字保持
        微软雅黑，只有读数位换等宽。
     ⑦ 门禁：新增 _gate_all.py（11 项一键跑，结果落 _gatelog/）、
        _p_v240_contrast.py（26 组 WCAG 对比度 + 明度阶梯 + 令牌引用完整性
        「含别名定义」+ 等宽字落地）、_p_v240_tagprio.py（tag 优先级规则自断言）、
        _p_v240_latestbg.py（应用级取色 + 抓图有效性守卫）。几何零漂移复核：
        左栏 417 / 右栏 733 / 卡片内边距 16 / 分隔条 10 / 行高 32 /
        可视高 407px ≈ 12.7 行，与 v2.3.1 逐项一致。

 17. v2.5.0：三栏浏览器式布局重构（信息架构级，功能原地保留）——
     ① 两栏 → 三栏：栏 1「导航」平台 → 芯片组（两级树）、栏 2「型号」当前芯片组的
        主板列表、栏 3「明细」BIOS 版本表 + 选中版本详情面板。四级层次（平台 →
        芯片组 → 型号 → BIOS）摊到三栏级联，最贴近浏览器行为。
        实测量化依据：型号名 P90=251px / max=357px。单栏同时装芯片组+型号必须按
        max 撑宽到 417px，其中约 106px 是给 5% 的长名付的钱 —— 分栏后栏 1 只需装
        芯片组（190px），省下的宽度全归 BIOS 表。
        ⚠ 三栏并不省总宽：型号名长度不因分栏变小，还多付一条分隔条，故默认窗口
        1200×780 -> **1440×820**（最小 1100 -> 1240）。1440 是让「栏 3 表格容器 ≥
        四列实测所需 726 + 单元格内边距 32」的最小整数宽（1420 时说明列还差 4px，
        半个字符，实测发现）。
     ② 跨三栏底部工具条：把「保存目录 + 操作按钮 + 进度条」从栏 3 卡片内部提到
        窗口底部、横跨三栏（Tk side="bottom" 是自下往上叠，故落在状态栏之上）。
        实测量化依据：目录路径原被截成 C:/Users/MSI/Downloa…（省略号）、进度条仅 298px；
        现在路径完整可见、进度条 ~660px、主按钮落到窗口右下角。
        实现是**最小侵入**：只把两行的父容器从右卡片换成 abar，控件本身与其 grid
        列配置一行未动；右卡片 row 3/4/5 高度随之归零，BIOS 列表（weight=1）接管。
        参照实现 asus_bios_checker v2.2.0 亦如此（该工具栏距用固定 PANE_GAP=12，
        本工具保留可拖拽分隔条 10px —— 属增强）。
     ③ 栏 3 底部「选中版本详情面板」：版本号 / 发布日期 / 大小 + [复制下载链接]
        [下载此版本] + **完整不截断**的说明 + SHA-256 行，落在 C_INSET 凹槽里。
        表格那一列只能显示一行且常被切，详情面板补上全文。
        ⚠ 阻断布局反馈环：说明的换行高会撑高详情区，而换行高又取决于可用宽度 ——
        闭环。解法是 wraplength 跟随**容器**宽度单向驱动 + DETAIL_MAX_LINES=4 封顶
        （参照实现在此踩过坑：列表区在 291~309px 抖动、极端一次被挤到 1px）。
        按钮直接复用既有 _menu_copy_url / _on_download，未新增下载路径。
     ④ 栏 1「折叠全部」+ 栏 2 footer：计数 v_cat 与目录时间戳 v_cat_upd 从栏 1 标题行
        挪到栏 2 底部（栏 1 变窄后被挤出卡片，实测时间戳被裁成 "…12:4("）。
        「折叠全部」按「当前是否有任一节点展开」决定本次收起还是展开，不额外记状态位
        -> 不会出现按钮文字与实际状态不同步。
        ⚠ 构建顺序坑：栏 2 在栏 1 **之前**构建，而 v_cat 原定义在栏 1 内 ->
        AttributeError；已把两个 StringVar 提前到状态初始化处。
     ⑤ 表列宽改按**实测内容需求**分配（推翻 v2.3.0 起的固定比例 0.22/0.15/0.10/0.53）：
        版本 118 / 发布日期 110 / 大小 86 / 更新说明 440（改前 153/104/84/356）。
        旧比例下 4 列有 3 列被截（date −6 / size −2 / note −60，合计缺 68px），
        同时版本列白占 35px —— 「分配 vs 需求」错配。现在四列全部不截断。
     ⑥ 行高拆分：芯片组行高 36 -> **26**、型号改独立样式 **30**（原与芯片组共用 36）。
        31 个芯片组 × 10px 省出约 310px 滚动高度；实测栏 1 可视芯片组从 ~16 增到 19+。
        数值对齐参照实现（芯片组 26 / 型号 30 / BIOS 表 32）。
     ⑦ CAT_INDENT 0 -> 6：v2.2.1 按用户要求把缩进归零（「文字全部贴近左边框」），
        但实测 indent=0 会把 ttk 的**展开指示器**挤到没有落脚宽度，平台行前渲染出
        豆腐块字形。6 是折中：保留「几乎贴边」的观感，又给指示器留出槽位。
        注：三栏化后芯片组已是**叶子节点**（型号迁到栏 2），只有平台行还带指示器。
     ⑧ 门禁重新基线：11 项全绿。新增 _p_v250_3col.py（三栏几何门禁，15 条断言：
        三栏 + 两条分隔条 = body 内容宽、分隔条宽度与布局、栏 1/2/3 各自设计区间、
        BIOS 表四列不溢出且占满容器、底部工具条跨全宽且位于卡片下方、详情面板已布局、
        搜索跨两栏），替掉断言「两栏之间那一条分隔条」的 _p_v231_split。
        另修 _opt_boot_flow 4 处 / _opt_gui 3 处**过期前提**（左栏「只扩不缩」、
        「列宽 ≥ 最长型号名需求」、「进度行与右栏同宽」—— 后者语义已反，进度行
        现在跨三栏）。行为层探针（弹簧/进度行/三级一致/对比度/tag 优先级/绿底/
        单元/下载）全部原样通过，说明三栏化未伤及行为层。

 18. v2.5.1：两处用户反馈修复 + 一处判据缺陷 ——
     ① 去掉「主板级提示框」：它取自 panel 的 note 字段（官方 SOP / Bilibili 或
        YouTube 教程 / 解压说明），原 pack 在表格下方，视觉上紧贴表格最后一行 ——
        读起来像「混进列表的数据行」（实测把「Youtube: MSI® HOW-TO use M-FLASH
        for BIOS」渲染成了一条列表项），干扰对 BIOS 行的扫读。控件与 StringVar
        保留（便于以后改挂到设置面板 / 关于页），这里统一不再 pack。
     ② 修栏 2 型号名被硬切：根因是**宽度需求少算** —— ttk Treeview 单元格的
        左内边距实测 17px，而旧代码只算了 S(1 + CAT_TREE_PAD) = 5px，漏掉 12px。
        实测后果：栏 2 列宽 301、文本可用只有 280，而 X870E 组里
        MEG X870E ACE MAX DRACO EDITION 需要 339 ⇒ 一批名字被切且**不带省略号**，
        看起来像渲染坏了。新增常量 CELL_PAD_X = 17 —— 它与 CAT_CARD_OVER 是
        **两个不同层次**的开销：前者管「列宽 -> 文本可用」，后者管「卡片宽 -> 列宽」。
     ③ 栏 2 超长名改为**尾部省略号** + 悬停显示完整名：新增 _ellipsize_board()
        与 _ellipsize()（纯 tkfont.measure 二分找最长前缀，不引入新依赖），列宽
        变化时重算显示文本。完整名一直保留在 iid_board 里，故 tooltip 与下载
        都不受影响。实测 X870E 组 22 款里只有 5 款需截断（其余完整显示），
        且被截的都有 … 标记 —— 从「看起来坏了」变成「明确告知被截」。
     ④ 默认窗口 1440 -> 1500：1440 是按「栏 2 用 5px 内边距」这个**错误需求**
        算出来的；修正后栏 2 需 +12，同时 BIOS 表说明列还得装下「最新」行的完整
        文本 —— 该行挂 FONT_B（('Microsoft YaHei UI', -18, 'bold')），比常规行
        FONT_S(-16) **既粗又大一号**，实测同一句 392 -> 447px（+14.0%）。旧列宽
        440 只够常规行，所以「表格里唯一被截的偏偏是最新那一行」。现在栏 3 = 829、
        表格容器 797、说明列 479（= 447 + 内边距 32），四列全部完整。
     ⑤ 门禁 11 项复跑全绿。

 19. v2.5.2：底部工具条的按钮重叠与间距口径 + 状态栏去重 ——
     ① 修「取消下载」盖住「打开目录」：btn_cancel 一直 grid 在 **column 3**，
        与 btn_open_dir 同格，而注释里写的却是「4 取消下载」（column 4 一直空着）。
        实测后果（交付前量化）：下载态 x=1191 w=99 与 x=1199 w=99 重叠 **91px**，
        取消下载盖掉打开目录 92%，只漏出右侧 8px 一条边，且重叠区两钮都可点。
        改为 column 4 后两钮各归其位。
     ② 修「打开目录」与「下载选中版本」缝隙 = **0px**：不是漏写 padx，而是
        **口径不统一** —— 间距挂在每个按钮**自己**的左 padx 上（btn_open_dir 吃
        (8,0)），于是「谁跟谁相邻」决定了「缝隙存不存在」；中间的按钮一旦被
        grid_remove，它带的那份间距也跟着消失。改为统一挂在**左元素的右 padx**
        （新常量 BTN_GAP = 10）：btn_pick / btn_open_dir / btn_cancel 各给一份，
        btn_dl 左 padx 归 0。现在空闲态与下载态的缝隙是同一个值，不必为两态写两套。
     ③ 状态栏右读数去掉「数据源」：它与栏 3 标题行右侧的数据源徽章完全重复，
        且措辞不一致（状态栏「数据源：中国站」vs 徽章「数据源 中国站」）。
        现徽章成为唯一承载者（它就贴在所描述的数据旁边），措辞统一为
        「· 数据源：x」；状态栏只留「v2.5.2 · DPI 150%」。
     ④ 新增门禁 _p_v252_btngap.py（10 条断言，A0-A6 / B1 / C1-C2），第 12 项。
        负向对照已验：换回 v2.5.1 源码时它报 6 项 FAIL（含精确复现的 91px 重叠），
        换回 v2.5.2 全绿 —— 不是恒真式。间距、重叠、文案未截、信息去重从此都有
        回归门。
     ⑤ 规范 §11.11 的第 2、3 项改写为实测结论（原描述是两栏时代的旧状态），
        新增 §11.13 记录本轮。

 20. v2.5.3：代码质量审计（**纯内部整理，界面与功能零变化**）——
     ① 去重：`_ellipsize` 有两份实现 —— 模块级（给右栏标题用）与 App._ellipsize
        方法（v2.5.1 给栏 2 加省略号时另写的），是同一套二分算法，只差量宽方式。
        方法改为委托模块级（measure=self._text_px，LRU 缓存收益不变），删掉
        8 行重复二分，将来改口径只需改一处。实测两版输出在 23 个型号 × 23 档列宽
        共 529 组组合上**完全一致**（差异 0），属纯去重、无行为变化。
     ② 删死语句：_init_dpi() 里 `global _DPI` 之后并无任何赋值（PLW0602）。
     ③ 删重复导入：文件头 `import hashlib` 写了两遍（F811）。
     ④ _gate_all.py 判据补齐：注释声明「FAIL / ✗ / 不符」三种失败行，代码里却只查
        了 FAIL 三兄弟 —— 注释与代码脱节（v2.5.1 的 btn_cancel 是同一类问题）。
        补齐前先核对 _gatelog/ 下 13 份历史日志，无任何一行以 ✗ / 不符 开头，
        故不会引入误报。
     ⑤ 记下一个**隐含耦合**（不改代码，只写进注释）：_text_px() 量宽用的是按
        FONT_S 建的 _fm_tree，而栏 2 的 _ellipsize_board() 也走它量型号名 ——
        两处字体**当前恰好同族同字号**才成立（Cat.Treeview 与 Mod.Treeview 都配
        font=FONT_S）。若将来给 Mod.Treeview 单独换字体而 _fm_tree 没跟着换，
        栏 2 省略号会静默算错。已写进 _text_px 的 docstring。
     ⑥ 新增门禁 _p_v253_ellipsis.py（E1-E5，第 13 项）：逐型号 × 逐列宽穷举，
        断言不溢出 / 不无谓省略 / 省略串是全名前缀 / 截得恰到好处 / 完整名仍保留
        在 iid_board。首版探针曾误报 31 条溢出，根因是没读回**真实**列宽（Tk 会把
        width 夹到 minwidth=293），已修正并写进探针注释。
     ⑦ 门禁 13 项复跑全绿。

 21. v2.5.4：`_build_ui` 拆分（**纯搬家，界面像素级不变**）——
     ① 585 行的单体方法拆成 16 个 `_ui_*` 段方法（窗口 / 品牌条 / 标题栏 / 状态栏 /
        工具条外壳 / 主体容器 / 栏1 目录树 / 分隔条 / 栏2 型号列表 / 栏3 BIOS 列表 /
        详情凹槽 / 空状态 / 操作行 / 进度行 / 结果横幅 / 收尾），`_build_ui` 只剩
        16 行调用。拆分由脚本按既有分节注释切行完成：除方法头之外一个字节没改，
        缩进与语句次序原样保留。
     ② 等价性不靠 review，靠冻结基线：新增第 14 项门禁 `_p_v254_uistruct.py`，
        固定 cwd（隔离用户 cfg）/ 固定 96 DPI / 固定 1440×820，深度优先导出
        **110 个控件 × 7 个字段**（Tk 路径名 / 类 / 管理器 / 实测几何 / 请求尺寸 /
        grid 参数 / pack 参数 / 显示文本），与 `_fixtures/ui_tree_baseline.json`
        逐条比对。路径名里带同父创建序号，所以"创建顺序被挪动"也会红。
        拆分前后实测差异 0 条。
     ③ 拆分本身引入了一个**静默 bug**，已修：`_ui_finish` 里写的是裸 `root`
        （原 `_build_ui` 的局部变量），拆出去后抛 NameError，被紧邻的
        `except Exception: pass` 吞掉 —— 后果是 WM_DELETE_WINDOW 协议静默失效、
        关窗不再保存窗口尺寸与目录树展开状态。控件树与实际界面**完全看不出**
        这个回归，故门禁补了一条运行时契约断言：该协议必须改绑到 `_on_close`。
     ④ 这条断言的第一版写成 `bool(root.protocol(...))`，是个**恒真式** ——
        Tk 的 WM_DELETE_WINDOW 一出生就绑着自己的 `destroy`，查询永远非空
        （实测 `'1820131180800destroy'`）。改为"与建窗时默认处理器比对 + 处理器名
        含 `_on_close`"，负向对照（改回裸 root）确认真的会红。
     ⑤ 门禁 14 项全绿；ruff 全仓 0 条。

技术要点：
  * 官网由 Akamai CDN 防护，普通 urllib/requests 会被 403/拦截，
    故网络层使用 curl_cffi 模拟 Chrome TLS 指纹（impersonate="chrome124"）。
  * 数据接口（官网前端同款）：
      GET /api/v1/product/getProductTagList?product_line=mb       -> 芯片组分类
      GET /api/v1/product/getProductList?product_line=mb&id[]=..  -> 按芯片组的型号列表
      GET /api/v1/product/support/panel?product=<slug>&type=bios  -> BIOS 列表
  * BIOS 文件直链 download.msi.com（Akamai 下载 CDN，支持断点续传）。

发行：江苏振远智能科技有限公司
"""
import ctypes
import hashlib
import json
import math
import os
import queue
import random
import re
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "微星主板 BIOS 下载工具"
APP_VERSION = "2.5.5"
APP_COMPANY = "江苏振远智能科技有限公司"

# ---------------------------------------------------------------- 常量
UA_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://www.msi.com"
API_PANEL = BASE + "/api/v1/product/support/panel?product={slug}&type={dtype}"
API_PL_TAG = BASE + "/api/v1/product/getProductTagList?product_line=mb"
API_PL_LIST = (BASE + "/api/v1/product/getProductList?product_line=mb"
               "&page_number=1&page_size=500&sort=1")
# 微星中国站：大陆在售/渠道型号（含全球站 API 没有的特供版），用于目录补全与 BIOS 回退
CN_BASE = "https://www.msi.cn"
CN_PL_LIST = (CN_BASE + "/api/v1/product/getProductList?product_line=mb"
              "&page_number=1&page_size=500&sort=1")
CN_API_PANEL = CN_BASE + "/api/v1/product/support/panel?product={slug}&type={dtype}"

IMPERSONATE = "chrome124"
# DNS 自愈（v2.3.3）：系统 DNS 无法解析官网域名（路由器/运营商递归 DNS 偶发故障，curl error 6/28）时，
# 自动改用 DoH 兜底 —— IP 直连不依赖系统 DNS。国内可直连的两个 DoH 服务，依次尝试。
DOH_URLS = ("https://223.5.5.5/dns-query",    # 阿里公共 DNS（RFC 8484）
            "https://1.12.12.12/dns-query")   # 腾讯 DNSPod（RFC 8484）

# ---- v2.2.0 DoH 健康记忆
# 旧版每次 DNS 失败都从 DOH_URLS 的第一个开始重试：若第一个恰好不通（被墙 / 服务
# 异常），每个请求都要白等一次超时；且同一批机器会在同一时刻同步重试。
# 这里记录「连续失败次数」，失败 ≥3 次的解析器降到队尾，一旦成功即清零。
_DOH_FAILS = {}
_DOH_DEMOTE_AT = 3


def _doh_order():
    """按健康度排序的 DoH 列表：健康的按原顺序在前，连续失败的排到队尾。"""
    def key(u):
        fails = _DOH_FAILS.get(u, 0)
        return (1 if fails >= _DOH_DEMOTE_AT else 0, DOH_URLS.index(u))
    return tuple(sorted(DOH_URLS, key=key))


def _doh_mark(url, ok):
    """记录一次 DoH 解析结果（成功清零，失败累加）。"""
    if ok:
        _DOH_FAILS.pop(url, None)
    else:
        _DOH_FAILS[url] = _DOH_FAILS.get(url, 0) + 1


def _backoff_delay(i, base=0.5):
    """第 i 次重试的等待时长：线性增长 + 随机抖动 + 上限（v2.2.0）。

    旧版 `0.5 * (i + 1)` 固定步长：多机 / 多请求会以完全相同的节奏重试，
    在最坏情况下把同一时刻的失败放大成同步的重试尖峰。
    """
    d = min(NET_BACKOFF_MAX, base * (i + 1))
    # 抖动加在上限**之内**：向上抖的部分会被 min 夹回上限，保证"上限"是真上限
    # （若先抖动再夹，或夹完再抖动，实际最大等待会变成 上限×1.25）
    return min(NET_BACKOFF_MAX,
               d * (1.0 - NET_BACKOFF_JITTER + 2.0 * NET_BACKOFF_JITTER * random.random()))
CATALOG_FILE = "msi_mb_catalog.json"     # 本地目录缓存
CFG_FILE = "msi_bios_checker.cfg"        # 用户设置（刷新间隔 / 显示范围）
# ---- 目录树列宽自适应参数（v2.1.1）
# 背景：主板型号名最长的 "MPG Z790 EDGE MONSTER HUNTER EDITION" 用 Microsoft YaHei
# 15px 实测 326px，加上 2 级缩进 21px 需要 ~353px 列宽；写死 300px 时右侧被裁
# （"…DRACO EPIC EDITION" / "…TOMAHAWK MAX WIFI PZ" 等 12 条型号名都读不全）。
CAT_INDENT = 6         # 每级缩进（设计基准 px），与 Cat.Treeview 的 indent 同源。
                       # v2.2.1：10→0（用户要求文字「全部贴近左边框」）。
                       # v2.5.0：0→6 —— 实测 indent=0 会把 ttk 的**展开指示器**
                       # 挤到没有落脚宽度，平台行前渲染出豆腐块字形（截图上是个「日」）。
                       # 6 是折中：既保留"几乎贴边"的观感，又给指示器留出槽位。
                       # 参照实现 asus_bios_checker v2.2.0 用 CAT_INDENT = 4 +
                       # CAT_IND_SLOT = 15；本工具 `_nav_col_need` 已按
                       # CAT_IND_PAD = 16 给带子节点的行预留了槽宽，所以只需修 indent。
                       # 注：三栏化后**芯片组已是叶子节点**（型号搬去栏 2），
                       # 只有平台行还带指示器，故缩进只影响平台行下方那 4px 的级差。
CAT_TREE_INIT = 300    # #0 列初始宽度（目录未加载时的观感，随后由实测值覆盖）
CAT_TREE_MIN = 220     # #0 列宽下限
CAT_TREE_PAD = 4       # 文本右侧留白
CAT_IND_PAD = 16       # 有子节点（会画展开箭头）时的额外偏移
CAT_CARD_OVER = 60     # 列宽之外左栏的固定开销（竖滚动条 + 内边距 + 边框，100% 实测）
CELL_PAD_X = 17        # ttk Treeview 单元格的**左内边距**（v2.5.1 实测，见规范 §11.12）。
                       # ⚠ 它与 CAT_CARD_OVER 是**两个不同层次**的开销，别混：
                       #     CAT_CARD_OVER 管「卡片宽 -> 列宽」；
                       #     CELL_PAD_X   管「列宽   -> 文本可用宽」。
                       #   旧代码只算了 S(1 + CAT_TREE_PAD) = 5px，漏掉这 12px ——
                       #   后果实测：栏 2 列宽 288、文本可用只有 271，而 X870E 组里
                       #   MAG X870E TOMAHAWK MAX WIFI 需要 275 ⇒ 一批名字被硬切
                       #   （无省略号，看起来像渲染坏了）。
CAT_RIGHT_MIN = 620    # 右栏（BIOS 明细）保底宽度：列宽不得挤占到该值以下
# ---- v2.3.1 左右栏可拖拽分隔
SPLIT_W = 10           # 分隔条命中宽度（设计像素）。10 而不是 1~2：1px 的线
                       # 好看但抓不住；10px 的透明区里放一条 1px 细线，
                       # 线负责"表达这里是分界"，宽区负责"鼠标别点空"
SPLIT_MIN_LEFT = CAT_TREE_MIN + CAT_CARD_OVER   # 左栏最小宽 = 树列下限 + 卡片开销
LEFT_RATIO = 0.30      # 左栏目标宽占布局区的比例（宽屏下用它避免右栏过宽）
LEFT_MAX = 470         # 左栏宽度上限：再宽就没有「目录/明细」的主次感了
# ---- v2.5.0 三栏浏览器式布局（导航 / 型号 / 明细）
# 以下常量一律是**卡片宽**（= 树列宽 + CAT_CARD_OVER），与 _set_col_widths 同口径。
#
# 宽度账（默认 1400 窗口）：内容宽 = 1400 − 40（左右外边距）− 20（两条分隔条）= 1340
#   栏1 220（芯片组名最长约 160 + 开销 60）
#   栏2 340（覆盖到型号名 P95 = 277，见实测分布 P50=167/P90=251/P95=277/max=357）
#   栏3 780 → 表格容器 748，> 四列所需 730 ⇒ **四列不再截断**
#   合计 220 + 340 + 780 = 1340 ✓
#
# 为什么不把栏2 定成「装下最长的那一款」：最大 357px 是 501 款里唯一一条
# "MPG Z790 EDGE MONSTER HUNTER EDITION"，为它把栏2 撑到 417 就要从 BIOS 表
# 抢走 77px（正是重构前的老问题）。改为覆盖 P95 + 悬停补全（_on_board_motion）。
NAV_COL_INIT = 250     # 栏 1（平台 / 芯片组导航）默认卡片宽
NAV_COL_MIN = 210      # 下限：再窄芯片组名就断了
NAV_TREE_MIN = 150     # 栏 1 的树列下限（区别于 CAT_TREE_MIN：导航栏只装
                       # 平台/芯片组名，最长约 190px，不需要 220 那么宽）
NAV_COL_MAX = 300      # 上限：导航不需要更宽，留白比宽度有用
BOARD_COL_INIT = 340   # 栏 2（型号列表）默认卡片宽
BOARD_COL_MIN = 240
BOARD_COL_MAX = 460
DETAIL_MIN = 720       # 栏 3（BIOS 明细）保底卡片宽：低于它表格四列必然互相挤
# BIOS 表各列的最小宽度（v2.5.0：列宽改按实测需求分配后，仍需下限兜底）
TV_COL_MIN = {"ver": 110, "date": 96, "size": 76}
TV_NOTE_MIN = 200
# v2.5.0 栏 3 底部详情面板（参照 asus_bios_checker v2.2.0）
RIGHT_DETAIL_MIN = 132   # 详情面板保底高（版本行 + 说明 4 行 + SHA-256 行）
# 「更新说明」在详情里最多显示的行数，超出以「…」收尾。
# ⚠ 必须封顶：详情区高由说明的换行高撑出，而换行高又取决于标签自己的宽度 ——
# 两者互为因果形成**布局反馈环**。华硕实测过同一窗口高度下列表区在 291~309px
# 之间抖动、极端一次把 BIOS 表挤到 1px。行数封顶后请求高有上界，环被切断。
DETAIL_MAX_LINES = 4
# ---- v2.5.5 栏 3 列表高度：按行数自适应，余量沉到卡片底部
# 为什么改：v2.5.0~v2.5.4 是「列表吃满剩余高度（weight=1）+ 详情保底 132」。
# 实测 3 行 BIOS 时列表区 368px、其中 278px 是纯空白（75%），而详情区被压在 126px。
# 表格底色与卡片同色、又无行分隔线，那片空白读起来像「表格还没加载完」。
# 现在：列表高度 = min(行数, TV_MAX_ROWS) 行，详情紧跟其下，剩下的高度作为
# **卡片底部的弹性空行** —— 读者的结论从「没加载完」变成「这张表就这么多行」。
TV_ROWH = 32           # 与 Treeview 样式 rowheight=S(32) 同源，改一处必须改两处
# 表头高只作**初值**：真实值由 _fit_tv_height 用 "控件请求高 − 行数×行高" 反推。
# 实测 96 DPI 下表头实占 43px（旧值 26 少算了 17px），而 17px 足够多挤进半行 ——
# 12 个版本时详情区正好被顶出卡片底部 11px（底部的 SHA-256 行看不见）。
TV_HEAD_H = 43
TV_MIN_ROWS = 3        # 再少也要留 3 行，避免 1 行数据时表格塌成一条
TV_MAX_ROWS = 12       # 再多也不放大：长表交给滚动条，而不是把详情挤出视野
# ---- v2.5.5 标题测量余量
# `font measure` 与 Label 实际 `winfo_reqwidth()` 不是同一个数：Tk 的 measure 对
# 整串一次性累加后取整，而 Label 的请求宽是逐字框累加再取整，比例字体下会差 1~4px。
# 实测 "MPG Z790 EDGE TI WIFI"（FONT_BOARD 26px bold）：measure 318 / reqwidth 322。
# 少了这个余量，就会出现「判定放得下 → 实际被 Label 硬切掉 4px」的尾巴 ——
# 而且没有任何省略号提示读者「这里还有字」。
TITLE_MEASURE_SLACK = 6
# ---- v2.5.2 底部工具条按钮间距
# 实测（_p_v252_btngap.py）：v2.5.1 里 `打开目录` 与 `下载选中版本` 的缝隙是 **0px**
# ——「选择… → 打开目录」有 8px 而它没有，右侧那对贴死得像一块连体按钮。
# 根因不是漏写 padx，而是**口径不统一**：间距挂在**每个按钮自己的左 padx** 上
# （btn_open_dir 吃 (8,0)），于是「谁跟谁相邻」就决定了「缝隙存不存在」；
# 一旦中间的按钮被 grid_remove（下载结束后 `取消下载` 隐藏），它的左 padx 也不
# 参与布局，缝隙随之消失。
#
# 统一口径：间距一律挂在**左元素的右 padx** 上，被隐藏的按钮不会把它带走。
#   btn_pick  → BTN_GAP
#   btn_open_dir → BTN_GAP
#   btn_cancel   → BTN_GAP（column 4，仅下载中显示）
#   btn_dl       → 0（间距由它左边那位提供）
# 这样空闲态与下载态的缝隙是同一个值，不需要为两态写两套。
BTN_GAP = 10
WIN_W = 1500           # v2.5.1：1440 -> 1500。1440 是按「栏 2 用 5px 内边距」的错误
                       # 需求算出来的；实测左内边距 17px 后栏 2 需要 +12，同时 BIOS 表
                       # 说明列还得装下「最新」行（挂 FONT_B，常态字 + 14%）的完整文本。
                       # 1440 -> 栏3 表格容器 758，够放「四列实测所需 726 + 单元格
                       # 内边距 32」。1420 时说明列还差 4px（半个字符），实测发现。
WIN_H = 820
MIN_WIN_W = 1180       # 最小窗口宽：三栏各自的下限之和 + 边距
MIN_WIN_H = 760
BODY_PAD_X = 20        # 布局区左右外边距（设计像素）。_build_ui 与 _left_limits
                       # 共用它 —— 两处各写一个 20 是"内容宽算错"的经典来源
# ---- 进度行文案宽度（v2.2.0 引入，v2.2.2 改为按真实文案实测）
# 完整文案 = 「已下载 / 总量 MB   速度   剩余时间   (百分比)」；窄窗口切成短文案
# （速度 + 百分比），把省下来的宽度还给进度条本身。
#
# v2.2.2 修正：v2.2.0 把「完整文案」的标签格写死 46 字符 —— 46 × 9px = 414px，而
# 完整文案真实最宽只有 374px，白占 40px；更要紧的是这条**估出来的假宽度**还被当成
# 降级阈值：默认 1200×780 在「目录加载完成、左栏由 360 扩到 417px」之后进度行掉到
# 699px < 728px，进度条被**永久**降级成短文案 —— 用户看不到总量 / 速度 / 剩余时间，
# 而窗口其实够宽（1280 就完全放得下）。实机日志原文：`进度文案压短（进度行 699px /
# 需要 728px）`。现在改为按下面两条**上界样例**实测像素宽预留，阈值与标签格宽共用
# 同一个值，不再有「估的宽度」参与判定。
PB_TXT_FULL = "88.8 / 188.8 MB   188.8 MB/s   剩 1:59:59   (100%)"   # 完整文案上界样例
PB_TXT_SHORT = "188.8 MB/s  100%"                                   # 短文案上界样例
PB_LBL_SHORT = 18      # 标签格下限（字符）
PB_LBL_SLACK = 6       # ttk 字符格度量差（设计像素，192 DPI 下实测 4~6px 取上界）
                       #   ttk.Label(width=N) 按字体**平均字符宽**算，比 measure("0")
                       #   宽约 0.5%；这 6px 必须计进 need，否则"判定为完整"时进度条
                       #   会被悄悄吃掉 6px、低于 PB_BAR_MIN。——防止极窄窗口下标签格抖到 0
PB_LBL_PAD = 1         # 字符格换算的安全余量（ttk.Label 的字格宽 ≠ measure("0")）
PB_BAR_MIN = 280       # 进度条本身至少保留的宽度（v2.2.2：300→280。旧值是按 46 字符格
                       # 的假宽度定的；改用真实文案宽后，默认 1200×780 下进度条实际有
                       # 311px、1100 短文案模式有 434px，280 已经足够）
# 目录自动刷新间隔选项：(天, 显示文案)，0 = 不自动刷新
REFRESH_OPTS = ((0, "不自动刷新"), (1, "1 天"), (3, "3 天"),
                (7, "7 天"), (14, "14 天"), (30, "30 天"))
DEFAULT_REFRESH_DAYS = 7
DEFAULT_CFG = {
    "refresh_days": DEFAULT_REFRESH_DAYS,  # 缓存超过 N 天启动时后台自动刷新；0 = 仅手动
    "show_platforms": None,                # None = 全部平台；否则为平台名列表
    "chip_filter": None,                   # None = 全部芯片组；否则为芯片组名列表
    # ---- v2.2.0 状态持久化：旧版只存上面三项，窗口位置 / 上次看的型号 /
    # 保存目录 / 目录树展开状态每次启动都要重新来一遍。
    "win": None,        # [设计宽, 设计高, 屏幕 x, 屏幕 y]；越界自动拉回屏幕内
    "last_slug": "",    # 上次查看的主板（启动后自动选中并载入）
    "last_title": "",   # 与 last_slug 配对，供状态提示显示
    "last_dir": "",     # 上次的 BIOS 保存目录
    "expanded": [],     # 目录树中手动展开的芯片组名（重启后自动还原）
    "left_w": 0,        # v2.3.1 用户拖拽出的左栏宽（v2.5.0 起废弃，仅读旧配置）
    "nav_w": 0,         # v2.5.0 栏 1（导航）用户拖拽宽（0 = 未拖过，走自适应）
    "board_w": 0,       # v2.5.0 栏 2（型号）用户拖拽宽（0 = 未拖过，走自适应）
}
# ---- v2.2.0 内存/缓存与调度策略参数
# 旧版的两处缓存（文本宽度、目录列宽需求）都是无上限 dict：键空间随目录 / 型号
# 增长，长时间使用会一直变大。这里统一换成有界 LRU 并给面板缓存定 TTL。
PX_CACHE_MAX = 4096          # 文本宽度缓存上限（条）
PANEL_CACHE_MAX = 64         # BIOS 面板内存缓存上限（款）
PANEL_TTL = 6 * 3600         # 面板缓存有效期（秒）—— 仅内存，不跨进程、不落盘
NET_BACKOFF_MAX = 8.0        # 网络退避上限（秒）
NET_BACKOFF_JITTER = 0.25    # 退避随机抖动比例（避免重试风暴同时打点）

# ================================================================ 微星红·深色电竞主题
# 层次：窗口底深炭 → 卡片深灰 → 输入/内嵌更深；MSI 红为唯一强调色
# 设计取向：电竞 hardware 气质，红条/红按钮/红色小标题贯穿全局
# v2.3.0：窗口底压暗一档（#1b1e24 → #16181e）。旧版卡片底(#23272f)与窗口底亮度只差
# 约 15%，卡片看起来是"贴在背景上的纸"；拉开后卡片靠明度就能"浮"起来，
# 不需要四边描边（见 _apply_style 的 Card.TFrame）。深色底同时让正文对比度更高。
C_BG = "#17191b"           # 窗口底（深炭）
C_CARD = "#272a2e"         # 卡片 / 面板
C_INSET = "#16181a"        # 输入条 / 内嵌分隔
C_BORDER = "#3b3f44"       # 分隔线 / 描边
C_TEXT = "#e6e8ea"         # 主文字（近白）
C_SUB = "#a8adb3"          # 次级文字
C_DIM = "#8f959e"          # 弱化 / 占位 / 状态栏
                           #   v2.4.0：由 #7d828a 提亮 —— 原色在卡片底上只有
                           #   3.92:1、状态栏上 4.08:1，都低于 WCAG AA 正文的
                           #   4.5。这是**改动前就存在**的欠债（基线 4.11 / 4.27），
                           #   借石墨精工这轮一并修到位。
C_CHIP = "#c9ced5"         # 芯片组行文字（目录树三级：TEXT 230 > CHIP 201 > SUB 174）
C_ACCENT = "#d81f26"       # MSI 红（品牌条 / 进度条 / 输入框 focus）
C_ACCENT_HOT = "#ff4438"   # 红 hover / 高亮
C_ACCENT_DEEP = "#a51410"  # 红 pressed
C_ACCENT_BTN = "#c81e24"   # 主操作按钮底（v2.3.5 加深：降低 ClearType 红透白字发虚）
C_ACCENT_BTN_HOT = "#e6332a"   # 主按钮 hover（比普通态亮一档、收敛不发粉）
C_ACCENT_BTN_DEEP = "#8f1216"  # 主按钮 pressed
C_ACCENT_BTN_DIS = "#7c2326"   # 主按钮 disabled 底
C_ACCENT_BTN_FG_DIS = "#eeb8b4"  # 主按钮 disabled 字（比旧 #e9c9c7 深一档，对比清晰）
C_MSI_RED = C_ACCENT       # 品牌条 / logo / 进度条
C_RED_HOT = C_ACCENT_HOT   # 亮红（v2.4.0 起不再用于卡片小标题 / 目录树平台行）
C_RED_BG = "#2e2123"       # 红弱背景（警示 / 危险容器）
C_SEL_BG = "#432b2b"       # 列表选中背景（暗红）
C_GREEN = "#63c98c"        # 成功
C_GREEN_BG = "#253329"
C_AMBER = "#e0b243"        # 警告
C_BLUE = "#6fa8e0"         # 信息/链接
C_BLUE_BG = "#243040"
C_STATUS_BG = "#202327"    # 状态栏底（v2.3.2 提亮：避开 #17191f 纯黑区 GDI 子像素补偿，消除文字橙红色环）
C_STATUS_FG = "#adb3bb"    # 状态栏文字（比 C_DIM 亮一档，ClearType 残影不可见）
C_BTN = "#32363a"          # 次级按钮底
C_BTN_DIS = "#2a2d31"      # 次级按钮禁用底（v2.5.5：tk.Button 禁用不会自动变暗，
                           # 必须显式给一个比常态更沉的底色，否则"禁用"看不出来）
C_BTN_HOVER = "#3e4247"    # 次级按钮 hover
C_BTN_PRESS = "#494e54"    # 次级按钮 pressed
C_HEADING = "#3a3f45"      # 表头底（v2.5.5：#32363a → #3a3f45。
                           # 旧值与卡片底 #272a2e 只差 12 级明度，表头与表体几乎
                           # 连成一片，只能靠字重区分；提亮后表头自然成为一条分隔带）
C_TROUGH = "#16181a"       # 进度条槽 / 滚动条槽
C_SCROLL = "#41464c"       # 滚动条滑块
# 标题栏跟随沉浸式深色：深色皮肤开启，与内容浑然一体
TITLEBAR_DARK = True
# ================================================================ DPI 感知（v2.1.0）
# 设计基准：96 DPI（Windows 100% 缩放）下的像素值。程序启动时**先**声明
# PerMonitorV2 感知、再创建 Tk，然后用 S(px) 把设计像素换算成当前 DPI 的物理像素。
#
# 为什么必须这样做：进程若声明「DPI 不感知」，Windows 会把整个窗口按缩放比
# **位图拉伸**（150% 下每个像素拉成 1.5 个），文字与图标全部发虚；声明感知后
# 由程序自己按物理像素绘制 —— 高缩放比下字形锐利、比例正确。
#
# 为什么字体也用 S()：负值字号是「像素级尺寸」，Tk 的 tk scaling 只作用于
# pt（正值）字号，负值一律按像素解释、不会自动随 DPI 放大，故必须手工换算。
DPI_BASE = 96
DPI_SCALE = 1.0        # 由 _apply_dpi_scale() 设置；100% 缩放时恒为 1.0
_DPI = DPI_BASE        # 探测到的真实 DPI


def S(px):
    """设计像素 → 当前 DPI 的物理像素（四舍五入；非零值至少 1px）。

    100% 缩放下 S(px) == px —— 与旧版渲染逐像素一致。
    """
    if not px:
        return 0
    v = int(round(px * DPI_SCALE))
    if v == 0:
        v = 1 if px > 0 else -1
    return v


_UI_FAMILY = None       # v2.2.1：实际选用的界面字族（首次探测后缓存）


def _ui_font_family():
    """挑一个本机真实存在、且深色背景下最清晰的界面字族（v2.2.1）。

    旧版写死 "Microsoft YaHei"。该字族在小字号（15~18px）下的 hinting 偏弱，
    深色底 + ClearType 次像素渲染时笔画边缘发虚、彩色描边明显（用户反馈
    「字体需要优化」的根因之一）。优先用同门的 **UI 变体** —— 它就是为界面
    字号设计的，字面更紧凑、stem 更稳；再依次回退到原字体与开源/系统替代。
    探测不到字族列表（没有 Tk 根窗口）时返回首选值且不写缓存，避免把
    「没探测」当成「不存在」永久记住。
    """
    global _UI_FAMILY
    if _UI_FAMILY:
        return _UI_FAMILY
    fams = set()
    try:
        r = tk._default_root
        if r is not None:
            fams = set(str(x) for x in r.tk.call("font", "families"))
    except Exception:
        fams = set()
    if not fams:
        return "Microsoft YaHei UI"
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans SC",
                 "PingFang SC", "SimHei", "SimSun"):
        if name in fams:
            _UI_FAMILY = name
            return name
    _UI_FAMILY = "Microsoft YaHei"
    return _UI_FAMILY


_MONO_FAMILY = None     # v2.4.0：读数用的等宽字族（首次探测后缓存）


def _mono_family():
    """挑一个本机真实存在的等宽字族 —— 用于**读数位**（时间戳 / 状态栏数据源）。

    v2.4.0「石墨精工」：等宽让数字逐位对齐、刷新时不左右抖，这是"仪表读数"质感的
    来源。首选 **Cascadia Mono**（微软出品）—— 它的 measure("0") 与 Microsoft
    YaHei UI 同为 9px（96 DPI / -16px 实测），数字部分宽度零漂移。Consolas 的
    -16px 实际渲染更小一档（控件高 31px vs 33px），故排在后面。

    探测不到字族列表时返回首选值且**不写缓存**（与 _ui_font_family 同一套理由：
    别把"没探测"当成"不存在"永久记住）；若本机一个等宽都没有，退回界面字族 ——
    宁可不换，也不让读数变成豆腐块。
    """
    global _MONO_FAMILY
    if _MONO_FAMILY:
        return _MONO_FAMILY
    fams = set()
    try:
        r = tk._default_root
        if r is not None:
            fams = set(str(x) for x in r.tk.call("font", "families"))
    except Exception:
        fams = set()
    if not fams:
        return "Consolas"
    for name in ("Cascadia Mono", "Cascadia Code", "Consolas",
                 "Sarasa Mono SC", "Sarasa Term SC", "DejaVu Sans Mono",
                 "Lucida Console", "Courier New"):
        if name in fams:
            _MONO_FAMILY = name
            return name
    _MONO_FAMILY = _ui_font_family()
    return _MONO_FAMILY


def _rebuild_fonts():
    """按当前 DPI_SCALE 重建全部字体元组（负值字号 = 像素，需手工缩放）。

    v2.2.1：字号整体上调一档、卡片小标题上调两档，把「窗口标题 / 卡片标题 /
    正文 / 次级说明 / 表格」五级拉开（旧版 -27/-20/-17/-15/-14，相邻层级只差
    2~3px，看上去糊成一片）。次级说明保留最小字号，但不再用 bold —— 小字号
    中文加粗在深色底上笔画会粘连，层级改由字号与颜色承担。
    """
    global FONT, FONT_B, FONT_ACCENT, FONT_S, FONT_SS, FONT_H, FONT_TITLE, FONT_BOARD, FONT_ICON, FONT_MONO
    fam = _ui_font_family()
    FONT = (fam, -S(18))                                # 正文 / 按钮
    FONT_B = (fam, -S(18), "bold")                      # 正文强调
    FONT_ACCENT = (fam, -S(19), "bold")                 # 主操作按钮：笔画更粗
    FONT_S = (fam, -S(16))                              # 表格 / 列表 / 状态栏
    FONT_SS = (fam, -S(15))                             # 次级说明
    FONT_H = (fam, -S(22), "bold")                      # 卡片小标题
    FONT_TITLE = (fam, -S(29), "bold")                  # 窗口大标题
    FONT_BOARD = (fam, -S(26), "bold")                  # 主板名标题
    FONT_ICON = (fam, -S(52))                           # 空状态图标
    # v2.4.0 石墨精工：等宽读数。**只落在不参与宽度竞争的位置** —— 目录更新时间戳、
    # 状态栏数据源读数、主板目录计数。这三处的容器宽度都由别的东西决定，换字体不会
    # 挤到邻居。进度文案**故意不用**：实测 PB_TXT_FULL 会从 374px 涨到 448px
    # （+19.8%），把 _fit_progress_text 的压短阈值从 685px 顶到 757px，于是默认
    # 1200 窗口（进度行 699px）会从"完整文案"变成"压短文案" —— 那是行为变化，越界。
    FONT_MONO = (_mono_family(), -S(16))


def _apply_dpi_scale(dpi):
    """设定缩放系数并重建字体（测试可强制指定 DPI 以验证高缩放比布局）。"""
    global _DPI, DPI_SCALE
    _DPI = max(DPI_BASE, int(dpi))
    DPI_SCALE = _DPI / float(DPI_BASE)
    _rebuild_fonts()


def _init_dpi():
    """声明 DPI 感知并探测真实 DPI —— **必须在创建 Tk 之前调用**。

    感知级别依次尝试：PerMonitorV2（Win10 1703+）→ PerMonitor（Win8.1+）→
    System（Vista+）；全部失败则维持系统位图缩放（等同旧版行为，不会更差）。
    """
    aware = False
    try:
        u32 = ctypes.windll.user32
        aware = bool(u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))   # PMv2
    except Exception:
        aware = False
    if not aware:
        try:
            aware = ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0        # PerMonitor
        except Exception:
            pass
    if not aware:
        try:
            aware = bool(ctypes.windll.user32.SetProcessDPIAware())            # System
        except Exception:
            pass
    dpi = DPI_BASE
    try:
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, 88))   # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
        except Exception:
            dpi = DPI_BASE
    _apply_dpi_scale(dpi)
    return aware


def _work_area():
    """主显示器工作区尺寸（物理像素；感知进程下即真实分辨率）。"""
    class _RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    r = _RECT()
    try:
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):
            if r.right > r.left and r.bottom > r.top:
                return (r.right - r.left, r.bottom - r.top)
    except Exception:
        pass
    try:
        return (ctypes.windll.user32.GetSystemMetrics(0),
                ctypes.windll.user32.GetSystemMetrics(1))
    except Exception:
        return (1280, 720)


def _fit_size(w, h, margin=0):
    """设计尺寸 → 物理像素，并夹紧到屏幕工作区内。

    高缩放比 + 小屏（如 1920×1080 @150%）时 S(1200)=1800 已接近满屏，
    不夹紧会让窗口（含最小尺寸）超出屏幕导致部分内容永远点不到。
    """
    aw, ah = _work_area()
    m = S(margin)
    return (min(S(w), max(320, aw - m)), min(S(h), max(240, ah - m)))


def _ellipsize(text, max_px, font_name, widget, measure=None, ell="\u2026"):
    """把文本裁到不超过 max_px，超出部分以 ell 结尾（按真实字模二分测量）。

    v2.2.0：用于右栏型号标题。标题用 24px 字，最长型号名约 560px，而右栏收到
    最小尺寸时只有约 620px —— 旧版把整串塞进 Label 会把右侧按钮挤出可视区。
    `measure` 可注入（测试用），默认走 Tcl 具名字体的 font measure。

    判定用的是 `measure(前缀 + ell)` **一次测量**（而不是「前缀宽度 + ell 宽度」
    两次相加）。两者在比例字体下有字距，理论上会差 1~2px；实测本工程这款字体
    在 23 个型号 × 23 档列宽上**结果完全一致**（`_p_v253_ellipsis.py` 有记录），
    所以这里取一次测量只是选个语义更直接的写法，不是修了一个已发生的 bug。
    """
    try:
        if measure is None:
            def measure(s):
                return int(widget.tk.call("font", "measure", font_name, s))
        if measure(text) <= max_px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if measure(text[:mid] + ell) <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return (text[:lo] + ell) if lo > 0 else ell
    except Exception:
        return text


def _ver_suffix():
    """状态栏版本号后缀：非 100% 缩放时附 DPI，便于确认感知已生效。"""
    if abs(DPI_SCALE - 1.0) < 0.001:
        return "v%s" % APP_VERSION
    return "v%s · DPI %d%%" % (APP_VERSION, int(round(DPI_SCALE * 100)))


# 初始（96 DPI）字体 —— 启动时 _init_dpi() 会按真实 DPI 重建
_rebuild_fonts()

# ---------------------------------------------------------------- 动效（v2.4.0）
# 统一帧动画：所有动画共用一个 after 循环，动画清空即停表 —— 空闲时零 CPU 占用
# v2.3.0：动效不再按"时长"配置，改为按弹簧参数（阻尼比 ζ / 响应 response，
# 见下方弹簧区块）。原来的 ANIM_FADE/ANIM_PB/ANIM_HOVER/ANIM_FLASH/ANIM_SHAKE
# 五个时长常量已被弹簧取代并删除 —— 留着的唯一后果是让人误以为改它们有效。
ANIM_FPS_MS = 16          # 帧间隔（~60fps）—— 弹簧按真实经过时间求值，与它无关
SEARCH_PH = "搜索型号 / 芯片组…"   # 搜索框占位文案

# ---------------------------------------------------------------- 弹簧（v2.3.0）
# Apple 流体交互：动画不是「固定时长的曲线」，而是有质量、有速度、**可随时改目标**的
# 弹簧。参数用 WWDC 的 (阻尼比 ζ, 响应 response) 二元素表示：ω₀ = 2π/response。
#   ζ = 1.0 临界阻尼 → 单调逼近，绝不抖（普通 UI 的默认）
#   ζ < 1.0 欠阻尼   → 过冲一次再回落，数值越小弹得越明显（只给带手势动量/瞬时反馈用）
# 官方参考：移动/画中画 1.0/0.4 · 旋转 0.8/0.4 · 抽屉 sheet 0.8/0.3；Web 默认 1.0，
# 手势抛动 ≈0.8。
SPR_VALUE = (1.00, 0.30)    # 通用值过渡（hover 配色 / 进度补间）：临界阻尼，永不抖
SPR_ENTER = (1.00, 0.35)    # 列表内容入场
SPR_BANNER = (0.80, 0.30)   # 结果横幅 / 设置面板出入场（对齐 Apple sheet 官方 0.8/0.3）
SPR_PRESS = (0.70, 0.22)    # 按钮按下回弹（有手势动量才允许弹）
SPR_SHAKE = (0.55, 0.32)    # 无效操作回摆（明显带回弹，但不失稳）
SPR_PULSE = (0.85, 0.40)    # 完成脉冲
SPR_EMPTY = (0.90, 0.40)    # 空状态入场

SPR_EPS_X = 0.0015          # 静止判据：位移阈值（相对值域，见 Spring.done）
SPR_EPS_V = 0.030           # 静止判据：速度阈值
PRESS_DARKEN = 0.18         # 按下状态层：在 hover 色基础上朝黑混 18%

C_ROW_HOVER = "#33373b"   # 列表行 hover 底（比卡片亮一档，不与选中暗红抢焦点）
C_LATEST_HOVER = "#2c4133"  # 「最新」行 hover 底（绿底提亮一档）
C_SKELETON = "#32363a"    # 骨架 / 占位行
# v2.2.1：空状态大图标专用色。旧版复用了 C_SKELETON —— 它在卡片底(#24262a)上的
# 对比度只有 **1.10:1**（实测屏幕取色 (42,47,57) vs (35,39,47)），等于那块区域
# 是空的：用户只看到一个孤零零的标题悬在中间。提到 2.5:1 后是一个「看得见的
# 水印」，既不抢正文，也不再像渲染错误。
C_WATERMARK = "#737880"   # 空状态图标（可见但克制的水印色）
TOAST_TRAVEL = 14         # 横幅入场位移（设计像素）—— 出场反向走同一条路径
PB_H = 10                 # 进度条高度（设计像素）—— 胶囊形，半径 = 高度/2
PB_R_STEP = 2             # 进度条槽与填充之间的留白（设计像素）
C_OK = "#41a873"          # 完成态（进度条红→绿脉冲目标）
C_OK_BG = "#223026"
C_OK_BORDER = "#3a6b53"


def _mix(c1, c2, p):
    """把 c1 朝 c2 混 p（0~1）—— 状态层叠加用（hover / 按下 / 禁用）。

    与 _lerp_color 同源，单独给个名字是为了让调用点读起来就是"叠加一层状态"。
    """
    return _lerp_color(c1, c2, p)


def _soft_clamp(x, cap, c=0.55):
    """软边界（Apple 橡胶缓冲）：|x| ≤ cap 时 **1:1 原样通过**，越界部分渐进吸收。

    注意这不是"整体缩放"：橡胶边界描述的是**越界后的位移映射**，界内必须原样跟随，
    否则手感会整体变软、失去"直接操纵"（direct manipulation）的跟手度。
    """
    if cap <= 0:
        return x
    a = abs(x)
    if a <= cap:
        return x
    over = a - cap
    a2 = cap + (1.0 - 1.0 / (over * c / cap + 1.0)) * cap
    return a2 if x > 0 else -a2


def _project(velocity, rate=0.998):
    """动量投射（Apple 官方公式）：由释放速度推算惯性终点位移。

        project(v) = (v/1000) * rate / (1 - rate)

    v 单位 px/s；rate 0.998 为普通滚动、0.99 更干脆。用于"甩动后该停在哪"的
    就近吸附（本工具暂无拖拽/甩动场景，作为弹簧工具箱的标准件提供并已单测）。
    """
    return (velocity / 1000.0) * rate / (1.0 - rate)


_MOTION_ON = None


def _motion_enabled():
    """系统「在 Windows 中显示动画」开关 —— 无障碍的"减弱动效"。

    对应 Apple 的 Reduce Motion。Windows 侧读 SPI_GETCLIENTAREAANIMATION(0x1042)：
    关闭时所有弹簧/补间**直接落到终值**，不产生任何过渡 —— 减弱动效要的是"不移动"，
    而不是"移动得更快"，所以不能退化成"时长缩短"。
    """
    global _MOTION_ON
    if _MOTION_ON is None:
        _MOTION_ON = True
        try:
            v = ctypes.c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0,
                                                          ctypes.byref(v), 0):
                _MOTION_ON = bool(v.value)
        except Exception:
            _MOTION_ON = True
        if not _MOTION_ON:
            _log("系统已关闭界面动画 → 全部过渡改为瞬时（减弱动效）")
    return _MOTION_ON


class Spring:
    """一维弹簧（**解析解**，帧率无关，可随时改目标）。

    为什么不用逐帧数值积分（半隐式欧拉）：
      * 它会在 ω₀·dt 不可忽略时引入**额外数值阻尼** —— 实测 ζ=0.55 的首次过冲从
        解析值 12.63% 掉到 10.86%，等于把设定的"弹跳强度"偷偷改小 14%；
        响应时间越短（ω₀ 越大）误差越大。参数就不再有明确物理含义了。
      * 解析解按"已流逝时间"求值，**天然帧率无关**：16ms 一帧与 50ms 一帧在同一
        时刻得到的位移逐位相同，不需要子步补偿。
      * 中途改目标 = 把当前 (x, v) 取作新初值、把 t 归零 —— 可打断与速度移交
        是同一个公式的自然结果。

    参数：ω₀ = 2π/response，σ = ζω₀，ω_d = ω₀√(1-ζ²)。
      ζ<1 欠阻尼：x = T + e^{−σt}[d₀cos(ω_d t) + (v₀+σd₀)/ω_d · sin(ω_d t)]
      ζ=1 临界  ：x = T + e^{−ω₀t}(d₀ + (v₀+ω₀d₀)t)
      ζ>1 过阻尼：x = T + c₁e^{r₁t} + c₂e^{r₂t}，r₁,₂ = −σ ± ω₀√(ζ²−1)
    （d₀ = x₀ − T）
    """

    def __init__(self, damping=1.0, response=0.35, value=0.0, target=0.0,
                 velocity=0.0):
        self.damping = float(damping)
        self.response = max(0.01, float(response))
        self.x = float(value)
        self.target = float(target)
        self.v = float(velocity)
        self._x0 = float(value)          # 本段运动的初值（retarget 时重置）
        self._v0 = float(velocity)
        self._t = 0.0                    # 本段已流逝时间

    @property
    def omega(self):
        return 6.283185307179586 / self.response

    def retarget(self, target, velocity=None):
        """改目标 —— **保留当前位移与速度**（这就是可打断）；可显式移交速度。"""
        if velocity is not None:
            self.v = float(velocity)
        self.target = float(target)
        self._x0, self._v0, self._t = self.x, self.v, 0.0

    def snap(self):
        """立即到位（减弱动效 / 初始化定位）。"""
        self.x = self.target
        self.v = 0.0
        self._x0, self._v0, self._t = self.x, 0.0, 0.0

    def advance(self, dt):
        """按墙钟时间 dt 推进，返回是否已静止。"""
        self._t += max(0.0, float(dt))
        self.x, self.v = self._at(self._t)
        if self.done():
            self.snap()
            return True
        return False

    def _at(self, t):
        """闭式解：给出运动开始后 t 秒的 (位移, 速度)。"""
        T, w0, z = self.target, self.omega, self.damping
        d0 = self._x0 - T
        v0 = self._v0
        if t <= 0.0 or (d0 == 0.0 and v0 == 0.0):
            return T + d0, v0
        s = z * w0
        if z < 1.0:
            wd = w0 * math.sqrt(1.0 - z * z)
            e = math.exp(-s * t)
            c, sn = math.cos(wd * t), math.sin(wd * t)
            x = T + e * (d0 * c + ((v0 + s * d0) / wd) * sn)
            v = e * (v0 * c - ((d0 * w0 * w0 + s * v0) / wd) * sn)
        elif z == 1.0:
            e = math.exp(-w0 * t)
            c = v0 + w0 * d0
            x = T + e * (d0 + c * t)
            v = e * (v0 - w0 * c * t)
        else:
            r = w0 * math.sqrt(z * z - 1.0)
            r1, r2 = -s + r, -s - r
            c2 = (v0 - r1 * d0) / (r2 - r1)
            c1 = d0 - c2
            e1, e2 = math.exp(r1 * t), math.exp(r2 * t)
            x = T + c1 * e1 + c2 * e2
            v = c1 * r1 * e1 + c2 * r2 * e2
        return x, v

    def done(self, eps_x=SPR_EPS_X, eps_v=SPR_EPS_V):
        """静止判据：位移与速度都小到看不见。

        阈值按目标量级自适应 —— 值域是像素时（如 120px）用绝对阈值会"永远差亿分之一"
        收不了尾；值域是 0~1 时又需要足够严。
        """
        scale = max(1.0, abs(self.target))
        if abs(self.x - self.target) > eps_x * scale:
            return False
        return abs(self.v) <= eps_v * scale


_KICK_CACHE = {}


def _kick_velocity(amp, damping, response):
    """反解"要让弹簧从 0 起步冲到峰值 amp，需要多大初速度"。

    用**运行时同一个解析解**按 1ms 采样量出单位速度脉冲的峰值再缩放 —— 比手写解析式
    可靠（三种阻尼分支都能覆盖），结果按参数缓存（抖动每次触发都要用）。
    """
    key = (round(amp, 4), damping, response)
    if key in _KICK_CACHE:
        return _KICK_CACHE[key]
    sp = Spring(damping, response, 0.0, 0.0, 1.0)
    peak = 0.0
    step = 0.001
    for i in range(1, 6001):
        sp.x, sp.v = sp._at(i * step)
        if abs(sp.x) > peak:
            peak = abs(sp.x)
        elif abs(sp.x) < peak * 0.02 and i * step > 0.2:
            break                    # 已过峰且衰减到 2% 以下 —— 不必扫满 6s
    val = (amp / peak) if peak > 1e-9 else 0.0
    _KICK_CACHE[key] = val
    return val


def _lerp_color(c1, c2, p):
    """两色线性插值（#rrggbb）。p<=0 返回 c1，p>=1 返回 c2。"""
    if p <= 0.0:
        return c1
    if p >= 1.0:
        return c2
    try:
        a = (int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16))
        b = (int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16))
        return "#%02x%02x%02x" % tuple(
            max(0, min(255, int(round(a[i] + (b[i] - a[i]) * p)))) for i in range(3))
    except Exception:
        return c2 if p >= 0.5 else c1


def _fmt_bytes(n):
    """人类可读体积：B / KB / MB / GB。"""
    try:
        n = float(n)
    except Exception:
        return "—"
    for unit, div in (("GB", 1073741824.0), ("MB", 1048576.0), ("KB", 1024.0)):
        if n >= div:
            return "%.1f %s" % (n / div, unit)
    return "%d B" % int(n)


def _fmt_eta(sec):
    """剩余时间：mm:ss / h:mm:ss。"""
    try:
        sec = int(max(0, sec))
    except Exception:
        return "—"
    if sec >= 3600:
        return "%d:%02d:%02d" % (sec // 3600, (sec % 3600) // 60, sec % 60)
    return "%d:%02d" % (sec // 60, sec % 60)


DL_CHUNK = 64 * 1024


# ---------------------------------------------------------------- 通用容器
class LRU:
    """有界 LRU 字典（v2.2.0）。

    用纯 dict "命中即挪到末尾" 实现，get/put 均摊 O(1)；超过 maxsize 时淘汰
    最久未使用项（dict 队首）。仅主线程访问，故不自带锁。
    """

    __slots__ = ("maxsize", "_d")

    def __init__(self, maxsize=512):
        self.maxsize = max(1, int(maxsize))
        self._d = {}

    def get(self, key, default=None):
        d = self._d
        if key in d:
            v = d.pop(key)
            d[key] = v          # 挪到末尾 = 标记为最近使用
            return v
        return default

    def put(self, key, value):
        d = self._d
        if key in d:
            d.pop(key)
        d[key] = value
        while len(d) > self.maxsize:
            d.pop(next(iter(d)))

    def pop(self, key, default=None):
        return self._d.pop(key, default)

    def clear(self):
        self._d.clear()

    def __len__(self):
        return len(self._d)

    def __contains__(self, key):
        return key in self._d


# ---------------------------------------------------------------- 日志/路径
def _app_dir():
    """程序目录：打包后为 exe 所在目录；源码运行时为当前工作目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.getcwd()


def _data_path(name):
    """数据文件路径：优先程序目录，只读 / 不可写时退回临时目录。探测时不创建空文件。

    （v2.0.0：原 _cache_path / _cfg_path 两段完全同构，合并到这里。）
    """
    p = os.path.join(_app_dir(), name)
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        return os.path.join(tempfile.gettempdir(), name)
    if os.path.isfile(p) or os.access(d, os.W_OK):
        return p
    return os.path.join(tempfile.gettempdir(), name)


def _cache_path():
    """目录缓存文件路径。"""
    return _data_path(CATALOG_FILE)


def _cfg_path():
    """用户设置文件路径。"""
    return _data_path(CFG_FILE)


def load_cfg():
    """读取用户设置；文件缺失/损坏/缺键/类型异常时回退默认值。"""
    cfg = dict(DEFAULT_CFG)
    try:
        p = _cfg_path()
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # v2.3.5 类型校验：手改损坏/旧版文件不致命
                if "refresh_days" in data:
                    try:
                        cfg["refresh_days"] = int(data["refresh_days"])
                    except (TypeError, ValueError):
                        cfg["refresh_days"] = DEFAULT_REFRESH_DAYS
                for k in ("show_platforms", "chip_filter"):
                    v = data.get(k)
                    cfg[k] = v if isinstance(v, list) else None
                # v2.2.0 状态字段的类型校验（手改损坏 / 旧版文件都不致命）
                win = data.get("win")
                if isinstance(win, (list, tuple)) and len(win) == 4:
                    try:
                        cfg["win"] = [int(win[0]), int(win[1]), int(win[2]), int(win[3])]
                    except (TypeError, ValueError):
                        cfg["win"] = None
                for k in ("last_slug", "last_title", "last_dir"):
                    v = data.get(k)
                    cfg[k] = v if isinstance(v, str) else ""
                exp = data.get("expanded")
                cfg["expanded"] = [x for x in exp if isinstance(x, str)] \
                    if isinstance(exp, list) else []
                # v2.3.1：左栏拖拽宽度（手改损坏 / 越界值一律回落为自适应）
                try:
                    lw = int(data.get("left_w") or 0)
                except (TypeError, ValueError):
                    lw = 0
                cfg["left_w"] = lw if lw > 0 else 0
                # v2.5.0：三栏的拖拽宽度。旧配置里的 left_w 不迁移 —— 两栏与
                # 三栏的宽度含义不同（旧 417 是「树含型号名」，新 220 是「仅导航」），
                # 硬套会让首次启动的栏 1 宽得离谱。直接走自适应。
                for _k in ("nav_w", "board_w"):
                    try:
                        _v = int(data.get(_k) or 0)
                    except (TypeError, ValueError):
                        _v = 0
                    cfg[_k] = _v if _v > 0 else 0
    except Exception as e:
        _log("load_cfg err: %r" % (e,))
    return cfg


def _atomic_write(path, text):
    """原子写文本：同目录临时文件 → flush + fsync → os.replace（v2.2.0 统一封装）。

    旧版 save_cfg / save_catalog 各写一份「tmp + os.replace」：改名本身是原子的，
    但**数据**并未落盘 —— os.replace 只切换目录项，不保证文件内容已刷到磁盘。
    断电 / 拔盘时可能留下「名字对、内容空或半截」的配置或目录缓存。
    这里补 flush + fsync，并把两处重复实现合并为一份。
    """
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)
        return True
    except Exception as e:
        _log("atomic write err %s: %r" % (path, e))
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False


def save_cfg(cfg):
    try:
        return _atomic_write(_cfg_path(), json.dumps(cfg, ensure_ascii=False))
    except Exception as e:
        _log("save_cfg err: %r" % (e,))
        return False


_LOG_FILE = "msi_bios_checker.log"
_LOG_MAX = 1 << 20          # 1 MB：超过即轮转一次，避免长期运行把日志撑爆


_LOG_LOCK = threading.Lock()


def _log(msg):
    """追加一行日志；文件超过 _LOG_MAX 时先轮转为 .1（只保留一代）。

    v2.2.0：整段加锁 —— 目录抓取 / 型号查询 / 下载三个后台线程都会写日志，
    旧版无锁时「判大小 → os.replace 轮转 → 追加」三步可被另一线程插入，
    表现为日志丢行或半行。锁粒度是整次写入，一次 open/append/close，开销可忽略。
    """
    try:
        with _LOG_LOCK:
            p = os.path.join(_app_dir(), _LOG_FILE)
            try:
                if os.path.isfile(p) and os.path.getsize(p) > _LOG_MAX:
                    os.replace(p, p + ".1")
            except Exception:
                pass
            with open(p, "a", encoding="utf-8") as f:
                f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:
        pass


def _is_dns_error(e):
    """判断异常是否为 DNS 解析失败（curl error 6 Could not resolve / 28 Resolving timed out / DNSError）。"""
    try:
        m = str(e).lower()
    except Exception:
        return False
    return ("could not resolve" in m or "resolving timed out" in m
            or "dns" in type(e).__name__.lower() or "esolv" in m)


def _cr_get_dns_safe(url, **kw):
    """带 DNS 自愈的 GET：系统 DNS 解析失败（curl error 6/28）时自动改用 DoH 重试。

    用法与 curl_cffi requests.get 一致（headers / stream / timeout / impersonate 等命名参数原样透传）。
    先走系统 DNS（快）；解析失败时依次改用 DOH_URLS 里的 DoH（IP 直连，不依赖系统 DNS）。
    非 DNS 类异常立即上抛；DNS 兜底全部失败时抛出带中文说明的 RuntimeError。
    """
    from curl_cffi import requests as cr
    last = None
    chain = (None,) + _doh_order()      # None = 走系统 DNS；DoH 按健康度排序
    for i, doh in enumerate(chain):
        try:
            r = cr.get(url, **kw) if doh is None else cr.get(url, doh_url=doh, **kw)
            if doh is not None:
                _doh_mark(doh, True)
            return r
        except Exception as e:
            last = e
            if not _is_dns_error(e):
                raise                 # 非 DNS 问题（超时/连接/证书等）不改路径，原样上抛
            if doh is not None:
                _doh_mark(doh, False)
            if i < len(chain) - 1:
                time.sleep(_backoff_delay(i, 0.6))
    raise RuntimeError("网络 DNS 解析失败（已自动尝试备用解析仍不通）：%r" % (last,))


def clean_version(v):
    """展示用版本字符串（仅清洗空白）。"""
    if not v:
        return "—"
    return re.sub(r"\s+", "", str(v))


def slugify(name):
    """主板名 -> 官网 URL slug。'MPG Z490 GAMING EDGE WIFI (MS-7C79)' -> MPG-Z490-GAMING-EDGE-WIFI"""
    s = re.sub(r'[\(\（].*?[\)\）]', '', str(name or ""))
    s = re.sub(r'[^A-Za-z0-9]+', '-', s.upper())
    return s.strip('-')


_JUNK_TITLE = {"XX", "XXX", "TEST"}
def _is_junk_board(board):
    """过滤官网列表中的占位/配件条目（如 xx、TPM 2.0 Module、已移除占位）。"""
    title = (board.get("title") or "").strip().upper()
    if not title or title in _JUNK_TITLE or len(title) < 2:
        return True
    if re.search(r'\b(TPM|MODULE|ACCESSORY)\b', title):
        return True
    if "(REMOVE" in title or title.startswith("("):
        return True
    return False


# ================================================================ MSI API 客户端
class MsiApi:
    def __init__(self):
        from curl_cffi import requests as cr
        self._cr = cr
        self._sess = cr.Session(impersonate=IMPERSONATE, timeout=(15, 60))
        # curl_cffi Session 非线程安全；所有请求加锁串行化
        self._lock = threading.Lock()

    def _get_json(self, url, retry=2):
        """GET JSON；v2.3.3 起带 DNS 自愈：系统 DNS 解析失败时自动改用 DoH 兜底重试。
        尝试序列：普通请求 retry 次 →（若为 DNS 错误）按健康度依次 DoH 再试。
        v2.2.0：DoH 走健康排序并回写结果；退避改为带抖动的有上限延时。"""
        last = None
        last_dns = False
        is_cn = url.startswith(CN_BASE)
        hdrs = {"User-Agent": UA_CHROME,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9" if is_cn else "en-US,en;q=0.9",
                "Referer": (CN_BASE + "/") if is_cn else (BASE + "/")}
        dohs = _doh_order()
        n = retry + len(dohs)
        for i in range(n):
            if i >= retry and not last_dns:
                break                 # 普通重试次数耗尽且并非 DNS 错误 → 不再多试
            doh = dohs[i - retry] if i >= retry else None
            with self._lock:
                try:
                    r = self._sess.get(url, headers=hdrs, doh_url=doh)
                    if r.status_code == 200:
                        if doh is not None:
                            _doh_mark(doh, True)
                        return r.json()
                    last = "HTTP %s" % r.status_code
                    last_dns = False      # 服务器有响应 → 不是解析问题，DoH 不算失败
                except Exception as e:
                    last = repr(e)[:160]
                    last_dns = _is_dns_error(e)
                    if last_dns and doh is not None:
                        _doh_mark(doh, False)
            if i < n - 1:
                time.sleep(_backoff_delay(i))
        if last_dns:
            raise RuntimeError("网络 DNS 解析官网失败（已自动尝试备用解析仍不通）：%s" % last)
        raise RuntimeError("请求失败: %s" % last)

    # ---------------- 芯片组分类（getProductTagList, type=3 为芯片组）
    def get_chipset_tags(self):
        j = self._get_json(API_PL_TAG)
        out = []
        for grp in (j.get("result") or {}).get("filterTagList") or []:
            if grp.get("type") != 3:
                continue
            for t in grp.get("tag") or []:
                title = str(t.get("title") or "").strip()
                if not title or not (title.lower().startswith("intel ") or
                                     title.lower().startswith("amd ")):
                    continue
                out.append({"id": t.get("id"), "title": title})
        return out

    # ---------------- 型号列表（可按芯片组 tag id 过滤）
    def get_product_list(self, tag_id=None):
        url = API_PL_LIST + ("&id[]=%s" % tag_id if tag_id else "")
        j = self._get_json(url)
        res = j.get("result") or {}
        items = []
        for it in res.get("getProductList") or []:
            title = (it.get("title") or "").strip()
            link = (it.get("link") or "").strip()
            if not title:
                continue
            items.append({"id": it.get("id"), "title": title,
                          "slug": link or slugify(title)})
        return items

    # ---------------- panel：BIOS 明细
    def get_bios_panel(self, slug, dtype="bios"):
        """查询 BIOS 面板。先查全球站 msi.com；若该型号全球站无数据
        （中国大陆特供 / 渠道板，如 B760M BOMBER、PRO B760M-X II），
        自动回退中国站 msi.cn。返回 (result_or_None, 'com'|'cn')。"""
        last_res, last_host = None, "com"
        for host, url in (("com", API_PANEL.format(slug=slug, dtype=dtype)),
                          ("cn", CN_API_PANEL.format(slug=slug, dtype=dtype))):
            try:
                j = self._get_json(url)
            except RuntimeError:
                if host == "com":
                    continue              # 全球站失败/无数据 -> 试中国站
                raise
            res = j.get("result")
            if not isinstance(res, dict):
                if host == "com":
                    continue
                break
            last_res, last_host = res, host
            if res.get("downloads"):
                return res, host          # 有有效 BIOS 数据
        return last_res, last_host

    def parse_bios_groups(self, panel):
        """从 panel result 提取分组: {badge: [items...]}，保持官网顺序。
        返回 (groups, os_list, note, title)"""
        dl = panel.get("downloads") or {}
        type_title = dl.get("type_title") or []
        if not type_title:
            for k, v in dl.items():
                if isinstance(v, list) and k not in ("type_title", "os"):
                    type_title.append(k)
        groups = {}
        for badge in type_title:
            items = dl.get(badge)
            if isinstance(items, list):
                groups[badge] = items
        return groups, dl.get("os"), panel.get("note"), \
            (panel.get("title") or panel.get("category") or "")


# ================================================================ 目录构建
def fetch_catalog(api, progress=None):
    """从官网构建完整主板目录。
    返回: {'updated': str, 'total': int,
           'brands': [{'name':'Intel','count':n,'chipsets':[
                        {'name':'Z890','boards':[{id,title,slug},...]}, ...]}, ...],
           'uncovered': [board...]}
    """
    if progress:
        progress("正在获取官网芯片组分类…")
    chipsets = api.get_chipset_tags()
    if not chipsets:
        raise RuntimeError("官网芯片组分类为空")
    if progress:
        progress("正在拉取全量型号列表…")
    full = api.get_product_list(None)
    if not full:
        raise RuntimeError("官网型号列表为空")
    full_clean = [it for it in full if not _is_junk_board(it)]

    # 按芯片组逐个过滤拉型号 -> 归属芯片组
    brands = {}          # name -> {'count':0, 'chipsets': [ {name, boards} ] }
    covered = set()

    def _add_board(brand, chip, board):
        b = brands.setdefault(brand, {"count": 0, "chipsets": []})
        cs = None
        for c in b["chipsets"]:
            if c["name"] == chip:
                cs = c
                break
        if cs is None:
            cs = {"name": chip, "boards": []}
            b["chipsets"].append(cs)
        cs["boards"].append(board)
        b["count"] += 1

    n = len(chipsets)
    for i, ct in enumerate(chipsets):
        title = ct["title"]
        if progress:
            progress("[%d/%d] %s" % (i + 1, n, title))
        try:
            items = api.get_product_list(ct["id"])
        except Exception as e:
            _log("chipset fetch err %s: %r" % (title, e))
            items = []
        brand = "Intel" if title.lower().startswith("intel ") else "AMD"
        chip = re.sub(r'^(Intel|AMD)\s+', '', title, flags=re.I).strip() or title
        seen = set()
        for it in items:
            if it["id"] in seen or it["id"] in covered:
                continue
            seen.add(it["id"])
            _add_board(brand, chip, it)
            covered.add(it["id"])

    # 全量列表里未被任何芯片组覆盖的型号 -> 归入「其他」
    uncovered = [it for it in full_clean if it["id"] not in covered]
    if uncovered:
        brand_other = {"count": 0, "chipsets": []}
        cs_other = {"name": "其他 / 未分类", "boards": []}
        for it in uncovered:
            cs_other["boards"].append(it)
            brand_other["count"] += 1
        if cs_other["boards"]:
            brand_other["chipsets"].append(cs_other)
        brands["其他"] = brand_other

    # 组装（Intel / AMD 顺序固定，其他最后）
    out_brands = []
    for name in ("Intel", "AMD", "其他"):
        if name in brands:
            b = brands[name]
            for cs in b["chipsets"]:
                # 按芯片组内型号数量从多到少？保持官网返回顺序更贴近产品线；去重保序
                seen = set()
                kept = []
                for x in cs["boards"]:
                    if x["id"] in seen:
                        continue
                    seen.add(x["id"])
                    kept.append(x)
                cs["boards"] = kept
            out_brands.append({"name": name, "count": b["count"],
                               "chipsets": b["chipsets"]})
    cat = {"updated": time.strftime("%Y-%m-%d %H:%M"),
           "total": len(full_clean), "brands": out_brands, "uncovered": []}
    # 中国站补全：把 msi.cn 在售但全球站 API 缺失的型号（大陆特供等）补录进来
    merge_cn_products(cat)
    return cat


_CN_CHIP_RE = re.compile(r'^(Z|B|H|X|A|TRX|WRX)\d{2,3}[A-Z]?$', re.I)


def merge_cn_products(cat):
    """微星中国站(msi.cn)目录补全。

    拉取中国大陆全量在售主板列表，与 cat 现有型号比对：
      * 已记录（slug / title 归一化命中）→ 滤过
      * 未记录且非占位 → 按标题中的芯片组码归入对应平台/芯片组并补录
        （如 B760M BOMBER / PRO B760M-X II / Z790MPOWER / B450 TOMAHAWK MAX 等）
      * 归属不到芯片组 → 收进「其他 / 未分类」

    就地修改 cat（在 fetch_catalog 流程里被调用，也支持对旧缓存文件复用）。
    返回补录的 [(title, slug, "平台/芯片组"|"其他")]；网络失败返回 None（调用方忽略）。
    """
    try:
        r = _cr_get_dns_safe(CN_PL_LIST, impersonate=IMPERSONATE, timeout=25,
                             headers={"User-Agent": UA_CHROME,
                                      "Accept": "application/json,text/plain,*/*",
                                      "Accept-Language": "zh-CN,zh;q=0.9"})
        try:
            j = r.json()
        finally:
            r.close()
        items = (j.get("result") or {}).get("getProductList") or []
    except Exception as e:
        _log("cn merge fetch err: %r" % (e,))
        return None
    if not items:
        return []

    def norm(s):
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    # 1) 现有型号登记
    known = set()
    for b in cat.get("brands") or []:
        for cs in b.get("chipsets") or []:
            for bd in cs.get("boards") or []:
                known.add(norm(bd.get("slug", "")))
                known.add(norm(bd.get("title", "")))

    # 2) 芯片组别名：从现有 catalog 提取 (码, 平台)，斜杠组合（X870E/X870）拆分，长码优先
    aliases = []
    for b in cat.get("brands") or []:
        bname = b.get("name")
        if bname == "其他":
            continue
        for cs in b.get("chipsets") or []:
            for sub in re.split(r"[/、,]", cs.get("name", "")):
                sub = sub.strip().upper()
                if _CN_CHIP_RE.match(sub):
                    aliases.append((sub, bname))
    aliases.sort(key=lambda x: -len(x[0]))

    def _find_brand(name):
        for b in cat.get("brands") or []:
            if b.get("name") == name:
                return b
        nb = {"name": name, "count": 0, "chipsets": []}
        cat.setdefault("brands", []).append(nb)
        return nb

    added = []
    for it in items:
        title = (it.get("title") or "").strip()
        link = (it.get("link") or "").strip()
        if not title or _is_junk_board(it):
            continue
        slug = link or slugify(title)
        if norm(slug) in known or norm(title) in known:
            continue
        # 归属
        brand = chip = None
        tu = title.upper()
        for code, bname in aliases:
            if code in tu:
                brand, chip = bname, code
                break
        b = _find_brand(brand or "其他")
        csname = chip if brand else "其他 / 未分类"
        cs = next((c for c in b["chipsets"] if c["name"] == csname), None)
        if cs is None:
            cs = {"name": csname, "boards": []}
            b["chipsets"].append(cs)
        board = {"id": it.get("id"), "title": title, "slug": slug}
        cs["boards"].append(board)
        b["count"] += 1
        added.append((title, slug, ("%s / %s" % (brand, chip)) if brand else "其他"))
        known.add(norm(slug))
        known.add(norm(title))
    if added:
        # 重算总款数（保证 total 与实际补录一致）
        total = sum(bd for b in cat.get("brands") or []
                    for cs in b.get("chipsets") or []
                    for bd in [len(cs.get("boards") or [])])
        cat["total"] = total
    return added


def save_catalog(cat):
    """写目录缓存（v2.2.0：复用 _atomic_write，带 fsync）。"""
    try:
        return _atomic_write(_cache_path(), json.dumps(cat, ensure_ascii=False))
    except Exception as e:
        _log("save_catalog err: %r" % (e,))
        return False


def load_catalog_cached():
    """读取本地缓存目录；不存在返回 None。返回 (catalog, age_seconds)"""
    try:
        p = _cache_path()
        if not os.path.isfile(p):
            return None, -1
        with open(p, "r", encoding="utf-8") as f:
            cat = json.load(f)
        age = time.time() - os.path.getmtime(p)
        return (cat if cat.get("brands") else None), age
    except Exception as e:
        _log("load_catalog err: %r" % (e,))
        return None, -1


# ================================================================ 下载
def _part_size(path):
    """已下分片大小（不存在 / 不可读返回 0）。"""
    try:
        return os.path.getsize(path) if os.path.isfile(path) else 0
    except Exception:
        return 0


def do_download(url, dest, progress_cb=None, cancel_event=None):
    """流式下载到 dest.part，完成后改名；返回 (ok, path, err, sha256_hex)

    注：curl_cffi 的 Response 不支持 `with` 上下文协议（区别于 requests），故手动 close。
    v2.3.3：DNS 解析失败时自动走 DoH 兜底重试（download.msi.com 同为 Akamai，可能解析故障）。
    v2.2.0：
      * **断点续传** —— dest.part 已存在时带 Range 从断点继续；服务端返回 206
        才按续传处理，返回 200（不支持 Range）则丢弃分片从头下，不会产生拼接坏文件。
        取消 / 失败时**保留** .part（这正是可续传的前提，旧版会删掉从头再来）。
      * **增量 SHA-256** —— 边下边算（续传时先对已有分片补算），下载完直接出摘要，
        不再像旧版那样把整个文件从头重读一遍（50MB 级 BIOS 省一次全量读盘）。
      * **落盘加固** —— 改名之前 flush + fsync，避免断电时"名字已改、内容未落盘"。
    """
    tmp = dest + ".part"
    headers = {"User-Agent": UA_CHROME}
    resume_at = _part_size(tmp)
    h = hashlib.sha256()
    if resume_at > 0:
        # 续传前先对已有分片补算摘要；读不动就放弃续传（重新全量下）
        try:
            with open(tmp, "rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
        except Exception as e:
            _log("续传补算摘要失败，改全量下载: %r" % (e,))
            resume_at = 0
            h = hashlib.sha256()
        else:
            headers["Range"] = "bytes=%d-" % resume_at
    r = None
    try:
        r = _cr_get_dns_safe(url, impersonate=IMPERSONATE, headers=headers,
                             stream=True, timeout=(20, 60))
        if r.status_code == 206:
            pass                                  # 服务端接受续传
        elif r.status_code == 200:
            if resume_at > 0:                     # 不支持 Range → 丢弃分片重来
                _log("服务端不支持 Range（返回 200），改为全量下载")
                resume_at = 0
                h = hashlib.sha256()
        else:
            return False, None, "服务器返回 HTTP %s" % r.status_code, None
        total = 0
        try:
            total = int(r.headers.get("Content-Length") or 0)
        except Exception:
            total = 0
        if resume_at > 0:
            m = re.search(r"/(\d+)\s*$", r.headers.get("Content-Range") or "")
            total = int(m.group(1)) if m else (total + resume_at)
        done = resume_at
        last = time.time()
        with open(tmp, "ab" if resume_at > 0 else "wb") as f:
            for chunk in r.iter_content(DL_CHUNK):
                if cancel_event is not None and cancel_event.is_set():
                    return False, None, "已取消", None      # 保留分片以便续传
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                now = time.time()
                if progress_cb and (now - last >= 0.08 or done >= total):
                    last = now
                    if not progress_cb(done, total):
                        if cancel_event is not None:
                            cancel_event.set()
                        return False, None, "已取消", None
            f.flush()
            try:
                os.fsync(f.fileno())              # 数据落盘后再改名
            except Exception:
                pass
        os.replace(tmp, dest)
        return True, dest, None, h.hexdigest()
    except Exception as e:
        return False, None, repr(e)[:200], None      # 保留分片（下次续传）
    finally:
        try:
            if r is not None:
                r.close()
        except Exception:
            pass


def sha256_file(path):
    """整文件 SHA-256 —— 仅作下载流内增量摘要缺失时的回退（见 do_download）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def parse_sha256_from_field(s):
    """'SHA-256:ea5f...<br>' -> hex 或 None"""
    if not s:
        return None
    m = re.search(r'[0-9a-fA-F]{64}', s)
    return m.group(0).lower() if m else None


def _safe_filename(url, ver=""):
    """从下载直链推导安全文件名（v2.0.0）。

    去掉查询串与路径分隔符，过滤 Windows 非法字符并剥掉首尾的「.」/空格，
    防止 `..` 或绝对路径让文件落到用户选定目录之外。
    """
    path = urllib.parse.urlparse(str(url or "")).path
    name = os.path.basename(path.rstrip("/").split("/")[-1])
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not name:
        v = ver if ver and ver != "—" else "download"
        name = "bios_%s.zip" % v
    if not re.search(r'\.(zip|rar|7z|exe)$', name, re.I):
        name += ".zip"
    return name


# ================================================================ 帧动画调度器
class PbarCanvas(tk.Canvas):
    """胶囊形自绘进度条（v2.3.0）。

    为什么换掉 ttk.Progressbar：ttk 的进度条在 Windows 上形状由主题决定 —— 永远是
    直角矩形，还自带一条浅色高光边；放在深色卡片上像一个"系统控件"，而不是一块
    "仪表"。自绘成胶囊（两端半圆）后，与按钮、卡片是同一套圆润的形状语言。

    兼容 ttk.Progressbar 的最小取值接口（`pb["value"]` / `pb.configure(value=)`），
    所以 _pb_set / _fit_progress_text 等既有逻辑一行都不用改。
    """

    def __init__(self, master, maximum=100.0, value=0.0, **kw):
        # 先备好字段：基类构造过程中会回调 configure → _redraw
        self._max = float(maximum) or 100.0
        self._value = float(value)
        self._fill = C_ACCENT
        self._idle = False
        tk.Canvas.__init__(self, master, **kw)
        self.bind("<Configure>", lambda e: self._redraw())

    # ---- ttk.Progressbar 兼容层
    def configure(self, cnf=None, **kw):
        if "value" in kw:
            self._value = max(0.0, min(self._max, float(kw.pop("value"))))
        if "maximum" in kw:
            self._max = float(kw.pop("maximum")) or 100.0
        if cnf:
            tk.Canvas.configure(self, cnf)
        if kw:
            tk.Canvas.configure(self, **kw)
        self._redraw()

    config = configure

    def __setitem__(self, k, v):
        if k == "value":
            self._value = max(0.0, min(self._max, float(v)))
            self._redraw()
        else:
            tk.Canvas.__setitem__(self, k, v)

    def __getitem__(self, k):
        if k == "value":
            return self._value
        return tk.Canvas.__getitem__(self, k)

    def set_fill(self, color):
        """填充色（完成脉冲红 → 绿 / 复位用）。"""
        self._fill = color
        self._redraw()

    def set_idle(self, on):
        """空闲态：槽也画成卡片底色，视觉上整条消失（v2.5.5）。

        为什么不用 pack_forget：工具条会因此矮掉 20px，窗口内容上下跳一次，
        下载一开始又要跳回来。进度条「不存在」只应该是视觉上的，不该改布局。
        """
        on = bool(on)
        if on == self._idle:
            return
        self._idle = on
        self._redraw()

    def _redraw(self):
        try:
            w, h = int(self.winfo_width()), int(self.winfo_height())
        except Exception:
            return
        if w < 4 or h < 2:
            return
        self.delete("all")
        self._pill(0, 0, w, h, C_CARD if self._idle else C_TROUGH)
        if self._idle:
            return
        frac = max(0.0, min(1.0, self._value / self._max))
        fw = w * frac
        if fw >= 1.0:
            self._pill(0, 0, fw, h, self._fill)

    def _pill(self, x0, y0, x1, y1, color):
        """圆头胶囊：两端半圆 + 中间矩形。

        不用 create_polygon(smooth=True)：那条路径在窄宽度下的圆角量由 Tk 自行插值，
        进度条从 0 起步时会先"鼓"一下再变长，观感不干净。
        """
        h = float(y1 - y0)
        r = h / 2.0
        span = float(x1 - x0)
        if span <= 1e-6:
            return
        if span <= 2.0 * r:                      # 太短 → 画一个整圆头，绝不溢出到左侧
            self.create_oval(x0, y0, x0 + 2.0 * r, y1, fill=color, outline=color)
            return
        self.create_oval(x0, y0, x0 + 2.0 * r, y1, fill=color, outline=color)
        self.create_rectangle(x0 + r, y0, x1 - r, y1, fill=color, outline=color)
        self.create_oval(x1 - 2.0 * r, y0, x1, y1, fill=color, outline=color)


class Anim:
    """统一帧动画调度器（v2.4.0）。

    所有动画注册到**同一个** after 循环：多个动画并行时只跑一个定时器，
    动画清空后自动停表 —— 空闲时零 CPU 占用。
    （若每个动画各起一个 after，空闲时仍会互相空转，是本工具要避免的。）

    同 key 再次 run() = 从 0 重新计时，天然支持"打断重来"（如进度条连续更新）。
    """

    def __init__(self, root):
        self.root = root
        self._items = {}       # key -> [t0, dur, on_frame, on_done]
        self._springs = {}     # key -> [Spring, on_frame, on_done]
        self._v_cache = {}     # key -> 最后一次的值（弹簧结束出表后仍可读，供重定向续接）
        self._last = None      # 上一帧墙钟（弹簧按真实经过时间积分）
        self._running = False
        self._seq = 0

    # ---------------------------------------------------------- 弹簧（v2.3.0）
    def spring(self, key, spec, on_frame, target, value=None, on_done=None,
               velocity=None):
        """注册 / 重定向一条弹簧动画。

        spec = (阻尼比 ζ, 响应 response)；on_frame(x, v) 收到的是**值域坐标**
        （不是 0~1 进度），x 可以短暂超出 [0,1]（欠阻尼过冲）。

        **同 key 再次调用 = 改目标并保留当前位移与速度**（可打断）——这正是与
        run()（同 key 从 0 重新计时）最关键的区别：旧版 hover 快速进/出时颜色会
        先跳回起点再走一遍，肉眼可见；弹簧是连续回摆。

        value=None 时用该 key 上一次的值起算（首次为 0）——这样"动画刚结束、
        用户马上反向操作"也能从终值平滑续接。
        """
        damping, response = spec
        tgt = float(target)
        if not _motion_enabled():
            x0 = self._v_cache.get(key, 0.0) if value is None else float(value)
            self._v_cache[key] = tgt
            try:
                on_frame(tgt, 0.0)
            except Exception as e:
                _log("spring instant err %r: %r" % (key, e))
            if on_done:
                try:
                    on_done()
                except Exception as e:
                    _log("spring done err %r: %r" % (key, e))
            return key
        st = self._springs.get(key)
        if st is None:
            x0 = self._v_cache.get(key, 0.0) if value is None else float(value)
            self._springs[key] = [Spring(damping, response, x0, tgt,
                                         0.0 if velocity is None else velocity),
                                  on_frame, on_done]
        else:
            st[0].retarget(tgt, velocity)
            st[1], st[2] = on_frame, on_done
        if not self._running:
            self._running = True
            self._last = time.monotonic()
            self.root.after(ANIM_FPS_MS, self._tick)
        return key

    def spring_set(self, key, target, velocity=None):
        """只改目标（保留速度）—— 用于"值已在途中，接着走"。"""
        st = self._springs.get(key)
        if st is None:
            return False
        st[0].retarget(target, velocity)
        return True

    def spring_x(self, key):
        """当前值与是否在跑：返回 float；从未出现过则 None。"""
        st = self._springs.get(key)
        if st is not None:
            return st[0].x
        return self._v_cache.get(key)

    def spring_drop(self, key):
        """从动画表里摘掉（不改值、不触发回调）——用于控件销毁前解绑。"""
        self._springs.pop(key, None)

    def run(self, dur, on_frame, on_done=None, key=None):
        if key is None:
            self._seq += 1
            key = "_a%d" % self._seq
        self._items[key] = [time.monotonic(), max(0.0, float(dur)), on_frame, on_done]
        if not self._running:
            self._running = True
            self.root.after(ANIM_FPS_MS, self._tick)
        return key

    def cancel(self, key):
        self._items.pop(key, None)

    def cancel_prefix(self, prefix):
        for k in [k for k in list(self._items)
                  if isinstance(k, str) and k.startswith(prefix)]:
            self._items.pop(k, None)

    def busy(self):
        return bool(self._items) or bool(self._springs)

    def _tick(self):
        now = time.monotonic()
        # ---- 弹簧：按**真实经过时间**积分（内部切 8ms 等长子步）
        # dt 上限 0.1s：窗口被拖动/卡顿后回来时不要一次补完，否则会瞬移。
        dt = 0.0 if self._last is None else max(0.0, min(0.1, now - self._last))
        self._last = now
        for key, st in list(self._springs.items()):
            sp, on_frame, on_done = st
            try:
                stopped = sp.advance(dt)
            except Exception as e:
                _log("spring step err %r: %r" % (key, e))
                stopped = True
            self._v_cache[key] = sp.x
            try:
                on_frame(sp.x, sp.v)
            except Exception as e:
                _log("spring frame err %r: %r" % (key, e))
                stopped = True
            if stopped:
                self._springs.pop(key, None)
                if on_done:
                    try:
                        on_done()
                    except Exception as e:
                        _log("spring done err %r: %r" % (key, e))
                if len(self._v_cache) > 512:        # 有界：别让长跑进程无限攒 key
                    for k in [k for k in list(self._v_cache)
                              if k not in self._springs][:256]:
                        self._v_cache.pop(k, None)
        for key, item in list(self._items.items()):
            t0, dur, on_frame, on_done = item
            # dur 单位是毫秒，time.monotonic() 差值是秒 —— 必须换算，否则动画慢 1000 倍
            p = 1.0 if dur <= 0 else (now - t0) / (dur / 1000.0)
            done = p >= 1.0
            if done:
                p = 1.0
            try:
                on_frame(p)
            except Exception as e:
                _log("anim frame err %r: %r" % (key, e))
                done = True
            if done:
                self._items.pop(key, None)
                if on_done:
                    try:
                        on_done()
                    except Exception as e:
                        _log("anim done err %r: %r" % (key, e))
        if self._items or self._springs:
            self.root.after(ANIM_FPS_MS, self._tick)
        else:
            self._running = False
            self._last = None          # 停表即清基准，避免下次起表把"空闲那段"算成一帧


# ================================================================ GUI
class App:
    def __init__(self, root):
        self.root = root
        self.api = MsiApi()
        self.q = queue.Queue()
        # 目录状态
        self.catalog = None
        self.cat_updated = ""
        self.cfg = load_cfg()           # 用户设置（刷新间隔 / 显示范围）
        self.iid_board = {}         # 目录树 iid -> (slug, title)
        # BIOS 查询状态
        self.cur_slug = None
        self.cur_title = ""
        self.cur_host = "com"        # 当前型号 BIOS 数据源：com=全球站 / cn=中国站
        self.groups = {}
        self.badges = []
        self.cur_badge = None
        self.cur_items = []
        self._loading_slug = None   # 正在查询的 slug（防同一型号重复请求）
        # 下载
        self.last_dir = self.cfg.get("last_dir") or None    # v2.2.0：恢复上次保存目录
        self.dl_thread = None
        self.dl_cancel = threading.Event()
        # ---- v2.2.0 并发 / 缓存状态
        # 在途任务计数：旧版用布尔 busy，两条请求重叠时先结束的那条会提前解除
        # 主按钮禁用（A 结束就 busy=False，而 B 还在跑）。改为计数后按「全部结束」解禁。
        self._inflight = 0
        # v2.5.5：主按钮的「在途禁用」标记。与 _inflight 分开是因为 _busy() 还会
        # 被下载态直接调用（下载不是队列任务，不计入 _inflight）。
        self._busy_flag = False
        self._title_full = "请先在左侧选择主板型号"   # 标题完整文本（省略前的原文）
        self._pb_compact = False                   # 进度文案是否处于窄窗口短格式
        self._cat_busy = False          # 目录抓取是否在途（4 个入口共用，防重复抓取）
        self._panel_cache = LRU(PANEL_CACHE_MAX)   # slug -> (ts, groups, note, host)
        self._panel_inflight = {}       # slug -> 在途标记（同型号请求合并）
        self._restored = False          # 上次查看的主板是否已恢复（只恢复一次）
        # ---- v2.4.0 动效 / 交互状态
        self.anim = Anim(root)
        self.v_search = tk.StringVar()      # 搜索框内容
        self._search_ph = True              # 占位文案是否显示中
        self._search_job = None             # 搜索防抖 after id
        self._search_q = ""                 # 生效中的过滤词（小写）
        self._search_hits = 0
        self._hover_row = None              # 列表 hover 行 iid
        self._latest_iids = set()           # 「最新」行 iid 集合（hover 变体用）
        self._iid_item = {}                 # 列表 iid -> BIOS 条目（选中项直接查）
        self._loading_name = None           # 加载态标题（None = 不在加载）
        self._loading_ticks = 0             # 加载点动画计数
        self._loading_job = None
        self._dl_speed = None               # 下载速度 EMA（B/s）
        self._dl_last_t = None
        self._dl_last_b = 0
        self._toast_job = None
        self._toast_fg = C_OK              # 横幅文字目标色（v2.3.0：出入场渐显用）
        self._dot_on = False               # 状态点是否正在呼吸（v2.3.0）
        self._dot_base = C_DIM             # 状态点常态色
        self._status_flash_n = None        # 状态栏闪烁计数状态（v2.3.0 弹簧链）
        # v2.3.1 布局：用户拖拽出的左栏宽（0 = 从未拖过，走自适应）
        self._left_user_w = int(self.cfg.get("left_w") or 0)
        # v2.5.0：两条导航栏各自的用户拖拽宽
        self._nav_user_w = int(self.cfg.get("nav_w") or 0)
        self._board_user_w = int(self.cfg.get("board_w") or 0)
        # v2.5.0 三栏状态
        self.iid_chip = {}        # 栏1：芯片组 iid -> (chipset dict, boards 列表)
        self._current_chip = (None, [])
        self._nav_need_key = None
        self._nav_need_v = 0
        self._board_need_key = None
        self._board_need_v = 0
        # v2.5.0：这两个 StringVar 现在被**栏 2 的 footer** 引用，而栏 2 在栏 1 之前
        # 构建 —— 必须提前到这里定义，否则 _build_ui 走到栏 2 时属性还不存在
        # （实测 AttributeError: 'App' object has no attribute 'v_cat'）。
        self.v_cat = tk.StringVar(value="加载中…")
        self.v_cat_upd = tk.StringVar(value="")
        self._split_drag = None            # 拖动起点 (x_root, 起始宽)，None = 未在拖
        self._title_refit_job = None       # 副标题变化后的空闲重算任务（v2.3.1）
        self._apply_palette()      # v2.5.5：必须早于建控件，见 _apply_palette docstring
        self._build_ui()
        self._apply_style()
        self._bind_shortcuts()
        self.root.after(120, self._poll_queue)
        self.root.after(180, self._apply_dark_titlebar)
        self.root.after(300, self._boot)

    # ------------------------------------------------------------- 样式（微星红 · 深色电竞主题）
    def _apply_palette(self):
        """全局调色板与原生控件选项 —— **必须在 _build_ui 之前**（v2.5.5）。

        这里踩过一个很贵的坑：`tk_setPalette` 不只是写 option 数据库，它还会
        **反向更新所有已存在控件**的颜色。原来它写在 `_apply_style` 里，而
        `_build_ui()` 先执行 —— 控件先建好、调色板后刷，于是每个 `ttk.Label`
        都被塞进一个显式的 `-background #17191b`（资源名正是 frameColor），
        压掉了自己样式里的 `background`。

        后果：卡片上每一处文字背后都垫了一条比卡片暗一档的横带（实测「主板目录」
        标签区像素 C_BG，卡片 C_CARD）。不刺眼，但整屏"脏" —— 这正是那种说不出
        哪里不对、又怎么看都不干净的感觉的来源。

        修法不是给几百个标签逐个补 `background=`，而是**把调色板提到建控件之前**，
        并立刻 `option_clear()` —— 调色板只管根窗口（Win11 DWM 下比
        `root.configure(bg=)` 可靠），不泄漏给随后创建的控件。
        清完再把真正需要 option 数据库的 tk 原生控件（Entry / Listbox / Combobox
        下拉）按主题色补回去。
        """
        self.root.configure(bg=C_BG)
        try:
            self.root.tk_setPalette(
                background=C_BG, foreground=C_TEXT,
                activeBackground=C_SEL_BG, activeForeground=C_TEXT,
                selectBackground=C_SEL_BG, selectForeground=C_TEXT,
                insertBackground=C_TEXT,
            )
        except Exception:
            pass
        # 顺序不能反：先清，再补 —— 补的条目本身也在数据库里，会被 clear 掉
        try:
            self.root.option_clear()
        except Exception:
            pass
        try:
            for _pat, _val in (
                    ("*Entry.selectBackground", C_SEL_BG),
                    ("*Entry.selectForeground", C_TEXT),
                    ("*Entry.insertBackground", C_TEXT),
                    ("*Text.selectBackground", C_SEL_BG),
                    # 全局 option（影响 Combobox 下拉等 tk 原生 popdown）
                    ("*TCombobox*Listbox.background", C_CARD),
                    ("*TCombobox*Listbox.foreground", C_TEXT),
                    ("*TCombobox*Listbox.selectBackground", C_SEL_BG),
                    ("*TCombobox*Listbox.selectForeground", C_TEXT),
                    ("*TCombobox*Listbox.font", FONT_S),
                    ("*Listbox.background", C_CARD),
                    ("*Listbox.foreground", C_TEXT),
                    ("*Listbox.selectBackground", C_SEL_BG),
                    ("*Listbox.selectForeground", C_TEXT)):
                self.root.option_add(_pat, _val)
        except Exception:
            pass

    def _apply_style(self):
        st = ttk.Style()
        self.st = st          # v2.4.0：进度条完成脉冲需在动效帧里改 style
        # 'alt' 主题在跨平台都完全支持 background 颜色覆写（clam 在 Win 下对 TFrame/Status/Treeview 硬编码 native look）
        for tname in ("alt", "clam", "xpnative", "default"):
            try:
                st.theme_use(tname)
                break
            except Exception:
                continue
        st.configure(".", font=FONT, background=C_BG, foreground=C_TEXT)
        # ---- 容器
        st.configure("TFrame", background=C_BG)
        # v2.3.0：四边同色描边 → 改由**明度**表达高度（见 C_BG 注释）。
        # 描边是"平面设计"的做法，会把卡片框死。
        # v2.4.0 更正：曾设想用 relief=groove + lightcolor/darkcolor 造"上受光/
        # 下背光"的立体边，实测在 alt 主题下 **lightcolor/darkcolor 不被尊重**，
        # 机制自算出一层固定的 +57 亮度跃升（(85,86,88) / (142,143,144)），在深色底
        # 上是刺眼白边 —— 见 _p_vis_style.py。故材质只能靠明度阶梯本身。
        # 顶点/底边高光由 _sky 与各分隔线承担，卡片本身不再画框。
        st.configure("Card.TFrame", background=C_CARD,
                     borderwidth=0, relief="flat", bordercolor=C_CARD)
        st.configure("StatusBar.TFrame", background=C_STATUS_BG)
        # ---- 文字
        st.configure("TLabel", background=C_BG, foreground=C_TEXT)
        st.configure("Card.TLabel", background=C_CARD, foreground=C_TEXT)
        st.configure("Sub.TLabel", background=C_CARD, foreground=C_SUB, font=FONT_S)
        # 进度文案标签专用：padding 归零 —— 让"字符格 × measure('0')"精确等于控件的
        # 像素占位（Sub.TLabel 实测多出左右各 2px），_pb_label_px() 与 _fit_progress_text
        # 的阈值才与真实布局严格自洽。
        st.configure("Pb.TLabel", background=C_CARD, foreground=C_SUB,
                     font=FONT_S, padding=0)
        st.configure("Dim.TLabel", background=C_CARD, foreground=C_DIM, font=FONT_S)
        # v2.4.0：等宽读数样式。**padding 与 Dim/Sub 一样不设** —— 设了会让标签
        # 多出左右各 2px 的占位（Sub.TLabel 实测如此），那就成尺寸变化了。
        st.configure("MonoDim.TLabel", background=C_CARD, foreground=C_DIM,
                     font=FONT_MONO)
        st.configure("MonoSub.TLabel", background=C_CARD, foreground=C_SUB,
                     font=FONT_MONO)
        st.configure("Title.TLabel", background=C_BG, foreground=C_TEXT, font=FONT_TITLE)
        st.configure("Ver.TLabel", background=C_BG, foreground=C_DIM, font=FONT_S)
        st.configure("Bold.TLabel", font=FONT_B, background=C_CARD, foreground=C_TEXT)
        st.configure("H.TLabel", font=FONT_H, background=C_CARD, foreground=C_TEXT)
        # v2.4.0 石墨精工：小标题不再吃红色预算。红色收归三处 —— 品牌锚点
        # （logo / 顶部品牌条）、唯一主按钮、进度条（属主操作流）。装饰性位置一律
        # 改由**明度**承担层级，红色才重新变回"有含义的信号"而不是背景装饰。
        st.configure("Section.TLabel", font=FONT_B, background=C_CARD, foreground=C_TEXT)
        st.configure("Board.TLabel", font=FONT_BOARD, background=C_CARD, foreground=C_TEXT)
        st.configure("Status.TLabel", background=C_STATUS_BG, foreground=C_STATUS_FG, font=FONT_S)
        # ---- 按钮：次级（深灰底 + 描边）
        st.configure("TButton", font=FONT, background=C_BTN, foreground=C_TEXT,
                     borderwidth=S(1), bordercolor=C_BORDER, focusthickness=0,
                     lightcolor=C_BTN, darkcolor=C_BTN,
                     padding=(S(14), S(6)), relief="flat")
        st.map("TButton",
               background=[("active", C_BTN_HOVER), ("pressed", C_BTN_PRESS),
                           ("disabled", "#272a2e")],
               foreground=[("active", C_TEXT), ("pressed", C_TEXT),
                           ("disabled", C_DIM)],
               bordercolor=[("active", "#575859"), ("disabled", "#303132")])
        # ---- 按钮：主操作（MSI 红）
        # v2.3.5：红底加深一档 + hover/pressed 联动收敛，降低 ClearType 红透白字的
        # 边缘混色；字号 FONT_ACCENT(-18px) 让白字笔画更粗实（像素实测实心率↑）
        st.configure("Accent.TButton", font=FONT_ACCENT, foreground="#ffffff",
                     background=C_ACCENT_BTN, borderwidth=0, focusthickness=0,
                     padding=(S(14), S(6)), relief="flat")
        st.map("Accent.TButton",
               background=[("active", C_ACCENT_BTN_HOT), ("pressed", C_ACCENT_BTN_DEEP),
                           ("disabled", C_ACCENT_BTN_DIS)],
               foreground=[("disabled", C_ACCENT_BTN_FG_DIS)])
        # ---- 下拉框（搜索框是自绘 tk.Entry，不走 ttk 样式，故不再配 TEntry）
        st.configure("TCombobox", font=FONT, fieldbackground=C_BTN, foreground=C_TEXT,
                     arrowcolor=C_TEXT, bordercolor=C_BORDER, lightcolor=C_BTN,
                     darkcolor=C_BTN, borderwidth=S(1), relief="flat", padding=S(3))
        st.map("TCombobox",
               fieldbackground=[("readonly", C_BTN), ("focus", C_BTN)],
               foreground=[("readonly", C_TEXT)],
               bordercolor=[("focus", C_ACCENT)])
        # ---- Treeview：BIOS 表
        # v2.3.1：行高 34→32 —— 配合底部省下的高度，最小窗口下可视行数从 9.9
        # 提到 12+；32px 仍是 16px 字的 2 倍，不挤（低于 30 中文就开始粘连）
        st.configure("Treeview", font=FONT_S, rowheight=S(32), background=C_CARD,
                     fieldbackground=C_CARD, foreground=C_TEXT,
                     bordercolor=C_BORDER, borderwidth=S(1), relief="flat")
        st.configure("Treeview.Heading", font=FONT_B, background=C_HEADING,
                     foreground=C_SUB, borderwidth=0, relief="flat",
                     padding=(S(10), S(7)))
        st.map("Treeview",
               background=[("selected", C_SEL_BG)],
               foreground=[("selected", C_TEXT)])
        st.map("Treeview.Heading",
               background=[("active", "#363a3f")],
               relief=[("active", "flat")])
        # ---- 目录树（左侧主板目录）
        # v2.5.0：芯片组行高 36 → 26。三栏后本栏**只装芯片组**（不再混装型号），
        # 行内容变短，36px 是多余的纵向开销 —— 31 个芯片组白占约 310px 滚动高度。
        # 同行参考：华硕工具同栏 rowheight = 26（本机 asus_bios_checker v2.2.0）。
        st.configure("Cat.Treeview", font=FONT_S, rowheight=S(26), background=C_CARD,
                     fieldbackground=C_CARD, foreground=C_TEXT,
                     bordercolor=C_BORDER, borderwidth=0, relief="flat",
                     # v2.3.7：indent 16→10（v2.3.4 收紧到 16 后用户仍觉偏大），
                     # 让 chipset 下的 board 型号（level 2）再往前缩 12px 紧凑显示
                     # v2.1.1：改为引用 CAT_INDENT，与列宽实测公式共用同一定义
                     indent=S(CAT_INDENT))
        st.map("Cat.Treeview",
               background=[("selected", C_SEL_BG)],
               foreground=[("selected", C_TEXT)])
        # 栏 2（型号列表）：行高独立成 30 —— 型号名比芯片组名长、需要更好扫读，
        # 但比旧的 36 紧凑。与华硕工具一致（型号栏 rowheight = 30）。
        st.configure("Mod.Treeview", font=FONT_S, rowheight=S(30), background=C_CARD,
                     fieldbackground=C_CARD, foreground=C_TEXT,
                     bordercolor=C_BORDER, borderwidth=0, relief="flat", indent=0)
        st.map("Mod.Treeview",
               background=[("selected", C_SEL_BG)],
               foreground=[("selected", C_TEXT)])
        # v2.1.1：建一个与 Cat.Treeview **同族同字号**的具名字体，供 Tcl font measure
        # 实测文本宽度（Tk 的 font 命令接受具名字体，测量值即渲染值）
        self._fm_tree = "catMeasure"
        self._px_cache = LRU(PX_CACHE_MAX)
        self._px_dpi = None
        try:
            self.root.tk.call("font", "delete", self._fm_tree)
        except Exception:
            pass
        try:
            self.root.tk.call("font", "create", self._fm_tree,
                              "-family", FONT_S[0], "-size", FONT_S[1])
        except Exception:
            self._fm_tree = None
        # v2.2.0：标题省略所需的同族同字号字体（Board.TLabel = FONT_BOARD）
        # v2.5.5：必须带 -weight / -slant，否则"测出来的宽度"和"画出来的宽度"不是一回事。
        #   FONT_BOARD = (fam, -26, "bold") → 渲染是粗体，测量字体却是常规体，
        #   实测同一串 "MPG Z790 EDGE TI WIFI"：measure 299px / 实际 reqwidth 322px，
        #   23px 的缺口足以让"测着放得下"的名字被 Treeview 式的硬切砍掉尾巴。
        self._fm_title = "boardMeasure"
        try:
            self.root.tk.call("font", "delete", self._fm_title)
        except Exception:
            pass
        try:
            self.root.tk.call("font", "create", self._fm_title,
                              "-family", FONT_BOARD[0], "-size", FONT_BOARD[1],
                              "-weight", FONT_BOARD[2] if len(FONT_BOARD) > 2 else "normal")
        except Exception:
            self._fm_title = None
        # v2.5.5：栏 2 footer 走等宽字体（FONT_MONO），时间戳要让路时得先量得准
        self._fm_mono = "monoMeasure"
        try:
            self.root.tk.call("font", "delete", self._fm_mono)
        except Exception:
            pass
        try:
            self.root.tk.call("font", "create", self._fm_mono,
                              "-family", FONT_MONO[0], "-size", FONT_MONO[1])
        except Exception:
            self._fm_mono = None
        # ---- 滚动条
        st.configure("Vertical.TScrollbar", background=C_SCROLL, troughcolor=C_TROUGH,
                     bordercolor=C_TROUGH, arrowcolor=C_SUB, borderwidth=0,
                     relief="flat", width=S(11))
        st.map("Vertical.TScrollbar",
               background=[("active", "#555657"), ("pressed", "#626365")])
        # ---- 进度条
        st.configure("TProgressbar", troughcolor=C_TROUGH, background=C_ACCENT,
                     bordercolor=C_TROUGH, lightcolor=C_ACCENT_HOT,
                     darkcolor=C_ACCENT_DEEP)
        # 列表行 tag
        try:
            # ⚠ v2.4.0 修复：**创建顺序即优先级**。
            # ttk::treeview 里一个 item 挂多个 tag、且这些 tag 都配置了同一个选项时，
            # 生效的是**创建顺序更早**的那个 —— 与 tv.item(tags=[...]) 的书写顺序无关。
            # （实测见 _p_v240_tagprio.py：先建 row 则 row 赢，先建 latest 则 latest 赢；
            #   把 tags 列表反写不改变结果。）
            #
            # "最新"行挂的是 tags=("latest", "row")，两个 tag 都配置了 background。
            # v2.4.0 之前这里先建 row 再建 latest，于是 row 的 C_CARD 一直盖住 latest 的
            # C_GREEN_BG —— 绿底从未渲染过（_p_v240_latestbg.py 实测 0 像素，v2.3.0 及
            # 更早的预览图同样如此，属**既有缺陷**而非视觉焕新引入）。
            # 现在把 latest 提到 row 之前创建，两者各自的语义才真正生效：
            #   最新行 -> 绿底 + 亮绿字（latest 赢）；普通行 -> 卡片底 + 主文字（只有 row）。
            # ---------------------------------------------------------------------
            # 最新版本行：深绿底 + 亮绿字（深色主题下用亮色保证对比度）
            self.tv.tag_configure("latest", background=C_GREEN_BG,
                                  foreground=C_GREEN, font=FONT_B)
            # 必须建在 latest **之后**（见上方说明）
            self.tv.tag_configure("row", background=C_CARD, foreground=C_TEXT)
            # v2.4.0：hover 变体（普通行 / 最新行各一套）。这两个 tag 是**单独挂载**的
            # （hover 行的 tags= 里不含 row/latest），不存在多 tag 冲突，所以顺序无所谓。
            self.tv.tag_configure("rowh", background=C_ROW_HOVER, foreground=C_TEXT)
            self.tv.tag_configure("latest_h", background=C_LATEST_HOVER,
                                  foreground=C_GREEN, font=FONT_B)
            # latest 非选中时显绿底，选中时由 selected map 接管成暗红
            try:
                st.map("Treeview",
                       background=[("selected", C_SEL_BG)],
                       foreground=[("selected", C_TEXT)])
            except Exception:
                pass
        except Exception:
            pass
        # 左侧目录树行 tag：平台亮白加粗 / 芯片组次亮 / 型号次级（v2.4.0 起纯明度分层）
        try:
            # v2.4.0 石墨精工：三级改由**明度**分层。原来 platform 用红色、chipset
            # 用亮白 —— 色相与明度两套编码混用；抽掉 platform 的红之后两级会同色，
            # 所以整体重排为 230 / 201 / 174 逐级递减。
            self.cat_tree.tag_configure("platform", foreground=C_TEXT, font=FONT_B)
            self.cat_tree.tag_configure("chipset", foreground=C_CHIP)
            self.cat_tree.tag_configure("board", foreground=C_SUB)
        except Exception:
            pass

    def _card(self, parent, **kw):
        return ttk.Frame(parent, style="Card.TFrame", padding=S(16))

    # v2.1.1：目录树列宽实测自适应相关（见 _cat_col_need / _text_px / _auto_fit_cat）
    _need_key = None      # 列宽需求的缓存键（DPI + 目录版本）
    _need_v = 0           # 缓存的列宽需求值
    _px_dpi = None        # 文本宽度缓存的 DPI 标记
    _px_cache = None      # LRU：{文本: 像素宽}（条数上限 PX_CACHE_MAX）
    _fm_tree = None       # 测量用 Tcl 具名字体（与 Cat.Treeview 同族同字号）
    _fm_title = None      # 测量用 Tcl 具名字体（与主板标题 Board.TLabel 同族同字号）
    _fm_mono = None       # 测量用 Tcl 具名字体（与栏 2 footer 的 FONT_MONO 同族同字号）

    # ------------------------------------------------------------- UI 布局
    def _build_ui(self):
        """装配窗口：本方法只保留**调用顺序**，实体在各 `_ui_*` 段方法里。

        v2.5.4 之前是 585 行的单体方法。这次拆分是纯搬家 —— 每段的语句、缩进、
        pack/grid 调用次序都与拆分前逐字一致，等价性由 `_p_v254_uistruct.py`
        逐控件比对 `_fixtures/ui_tree_baseline.json`（类 / 布局参数 / 实测几何 /
        文本）来保证，不靠肉眼 review。

        ⚠ 下面这 16 个调用的**先后不许重排**：Tk 的 pack 按调用先后分配空间，
        状态栏与底部工具条都 side="bottom"（先调用的更贴底），body 又是
        expand=True 吃掉剩余高度 —— 换一下顺序，整窗布局就变了。
        """
        self._ui_window()
        self._ui_brand()
        self._ui_header()
        self._ui_statusbar()
        self._ui_actionbar()
        body = self._ui_body()
        self._ui_cat_card(body)
        self._ui_split_bars(body)
        self._ui_board_card(body)
        rf = self._ui_bios_card(body)
        self._ui_detail_zone(rf)
        self._ui_empty_state()
        self._ui_download_row()
        self._ui_progress_row()
        self._ui_toast(rf)
        self._ui_finish()

    def _ui_window(self):
        """根窗口：标题、图标、几何恢复、最小尺寸、底色，以及充当天窗的 `_sky`。"""
        root = self.root
        root.title("%s v%s" % (APP_TITLE, APP_VERSION))
        # v2.0.0：源码运行时也带上窗口 / 任务栏图标（打包后由 exe 资源提供）
        try:
            _ico = os.path.join(_app_dir(), "msi_bios.ico")
            if os.path.isfile(_ico):
                root.iconbitmap(_ico)
        except Exception:
            pass
        # v2.2.0：恢复上次的窗口尺寸/位置。尺寸按设计像素存盘（跨 DPI 自动等比），
        # 位置是屏幕物理坐标；越界（换屏 / 拔掉外接显示器）则只用尺寸、回到默认位置。
        _win_w, _win_h, _geo = self._restore_geometry()
        root.geometry(_geo)
        # v2.5.0：三栏各自的下限之和 = 190 + 240 + 720 + 两条分隔条 20
        # + 左右外边距 40 = 1210；取 1180 作为最小宽（此时栏 3 会被挤到保底以下，
        # 但不会塌 —— 三栏布局在极窄窗口下优先级是「导航能用 > 明细完整」）
        root.minsize(min(S(MIN_WIN_W), _win_w), min(S(MIN_WIN_H), _win_h))
        root.configure(bg=C_BG)
        # 天窗：ttk 主题下 root 客户区仍走系统浅色，铺一个全屏 tk.Frame 充当天窗
        self._sky = tk.Frame(root, bg=C_BG)
        self._sky.pack(fill="both", expand=True)

    def _ui_brand(self):
        """顶部 2px 品牌条。Tk 没有渐变填充，用 24 个等宽 Frame 拼出来。"""
        # ---------- 顶部品牌条（v2.3.0：满幅纯红 → 红向右渐隐）
        # 旧版是 4px 的满幅纯红横贯整个窗口 —— 和左上 logo 红块、红色主按钮三处同时
        # 抢注意力，强调色被稀释成了"装饰"。现在只留 2px 的品牌锚点并向右渐隐到窗口底，
        # 视线自然落到左侧 logo；省下来的红色预算全部留给唯一的主动作按钮。
        self._brand = tk.Frame(self._sky, bg=C_BG, height=S(2))
        self._brand.pack(fill="x", side="top")
        _segs = 24
        for _i in range(_segs):
            _c = _lerp_color(C_MSI_RED, C_BG, (_i / float(_segs - 1)) ** 0.72)
            tk.Frame(self._brand, bg=_c, height=S(2)).pack(
                side="left", fill="both", expand=True)

    def _ui_header(self):
        """标题栏：左侧红色 logo 块 + 应用名；右侧设置按钮 + 版本/公司。"""
        # ---------- 标题栏
        head = ttk.Frame(self._sky, padding=(S(20), S(12), S(20), S(6)))
        head.pack(fill="x")
        logo = tk.Frame(head, bg=C_MSI_RED, width=S(10), height=S(28))
        logo.pack(side="left", padx=(S(0), S(12)))
        logo.pack_propagate(False)
        ttk.Label(head, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        # v2.2.0：右侧「设置 + 版本」放进同一容器，由 pack 在同一行里垂直居中 ——
        # 旧版两个控件各带不同 pady（4 / 10），底边差 6px，看起来就是没对齐。
        hright = ttk.Frame(head)
        hright.pack(side="right")
        self.btn_settings = ttk.Button(hright, text="设置", width=6,
                                       command=self._open_settings)
        self.btn_settings.pack(side="right", padx=(S(16), S(0)))
        ttk.Label(hright, text="%s   |   %s" % (_ver_suffix(), APP_COMPANY),
                  style="Ver.TLabel").pack(side="right")

    def _ui_statusbar(self):
        """状态栏：左侧状态点 + 状态文字，右侧版本/DPI 读数。"""
        # ---------- 状态栏（先 pack，让底部空间留给状态栏，避免被 body expand 挤掉）
        tk.Frame(self._sky, bg=C_BORDER, height=S(1)).pack(fill="x", side="bottom")
        sb = ttk.Frame(self._sky, style="StatusBar.TFrame", padding=(S(20), S(8)))
        sb.pack(fill="x", side="bottom")
        self.v_status = tk.StringVar(value="就绪")
        # v2.4.0：左侧状态圆点（颜色随语义变化）+ 状态文字（完成时做闪烁脉冲）
        self.dot_status = tk.Label(sb, text="●", font=FONT_S,
                                   bg=C_STATUS_BG, fg=C_DIM)
        self.dot_status.pack(side="left", padx=(S(0), S(8)))
        self.lbl_status = tk.Label(sb, textvariable=self.v_status, font=FONT_S,
                                   bg=C_STATUS_BG, fg=C_STATUS_FG, anchor="w")
        self.lbl_status.pack(side="left")
        # v2.5.5：右侧「v2.5.4」删掉了 —— 顶栏产品牌位已经写着同一个版本号，
        # 同一屏出现两次不会让人更确定，只会让人怀疑"这两个是不是不一样"。
        # 版本 + DPI 现在只由顶栏的 _ver_suffix() 承担。

    def _ui_actionbar(self):
        """底部工具条外壳：两行 grid —— 行 0 操作（`_ui_download_row` 填），行 1 进度（`_ui_progress_row` 填）。"""
        # ---------- 跨三栏底部工具条（v2.5.0，参照本机 asus_bios_checker v2.2.0）
        # 为什么升为全宽条：
        #   ① 纵向：旧版「操作行 50 + 进度行 25 + 两段行距 35」常驻在右卡片内部，
        #      占卡片高度约 17%；提到窗口底部后，这部分高度**全部还给 BIOS 列表**。
        #   ② 横向：保存目录路径在 790px 的右卡片里必被截断，全宽后可用 1360px。
        #   ③ 语义：主按钮从「右卡片右下角」挪到「窗口右下角」，更贴合"全局动作"。
        # pack 顺序：本块在状态栏之后 pack(side="bottom") —— Tk 的 bottom 是**往上叠**，
        # 所以工具条落在状态栏**上方**，与华硕工具一致。
        tk.Frame(self._sky, bg=C_BORDER, height=S(1)).pack(fill="x", side="bottom")
        abar = ttk.Frame(self._sky, style="Card.TFrame",
                         padding=(S(20), S(8), S(20), S(6)))
        abar.pack(fill="x", side="bottom")
        self._abar = abar
        abar.columnconfigure(0, weight=1)
        # 行 0：保存目录（吃剩余宽度）+ 路径操作 + 全局动作（右对齐）
        arow = ttk.Frame(abar, style="Card.TFrame")
        arow.grid(row=0, column=0, sticky="ew")
        arow.columnconfigure(0, weight=1)
        self._arow = arow
        # 行 1：进度条 + 速度 / 剩余时间
        prow = ttk.Frame(abar, style="Card.TFrame")
        prow.grid(row=1, column=0, sticky="ew", pady=(S(10), S(0)))
        self._prow = prow

    def _ui_body(self):
        """三栏主体容器。列 0/2/4 放卡片，列 1/3 是自绘分隔条，弹性权重只给列 4。"""
        body = ttk.Frame(self._sky, padding=(S(BODY_PAD_X), S(8), S(BODY_PAD_X), S(6)))
        body.pack(fill="both", expand=True)
        # v2.3.1：列 0=左卡片 1=分隔条 2=右卡片。弹性权重给 **列 2**（右卡片）——
        # 左卡片宽度始终由 _set_left_width 显式赋值，不会被 grid 传播改动。
        body.columnconfigure(4, weight=1)
        body.rowconfigure(0, weight=1)
        self._body = body
        return body

    def _ui_cat_card(self, body):
        """栏 1：主板目录树。宽度由 `_auto_fit_cat()` 显式赋值，故关闭 grid 传播。"""
        # ===== 左：主板目录树 =====
        lf = self._card(body)
        # v2.3.1：原 padx 右侧 12px 的固定空隙，改由分隔条承担（见下）
        lf.grid(row=0, column=0, sticky="nsew")
        # v2.1.1：左栏宽度由 _auto_fit_cat() 显式设定 = 目录树 #0 列宽 + CAT_CARD_OVER。
        # 必须关闭 grid 传播（默认开启时 -width 会被忽略；顺带一提原 pack_propagate
        # 对 grid 子控件无效，所以旧写法 lf.configure(width=356) 一直是空操作）。
        # 也不能靠"列宽经传播撑出卡片"：Tk 的 Treeview 在控件已映射后改列宽时
        # winfo_reqwidth() 不更新（实测列宽 351 而 reqwidth 仍 224）。
        lf.grid_propagate(False)
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(2, weight=1)      # 0=标题 1=搜索 2=树 3=无结果 4=更新信息
        self._lf = lf
        lhead = ttk.Frame(lf, style="Card.TFrame")
        lhead.grid(row=0, column=0, sticky="ew")
        ttk.Label(lhead, text="主板目录", style="H.TLabel").pack(side="left")
        # v2.5.0：计数的**显示位置**挪到栏 2 的 footer（见 _mf 的 mfoot）。
        # 原因：栏 1 只有 250px，「主板目录 + 共 501 款 + 折叠全部 + ↻」四项挤在
        # 一行里必然互相压；而计数描述的是**整个目录**，放在横跨中栏的 footer 更合适。
        # 变量本身保留（_populate_tree 多处仍在 set）。
        # v2.5.0：新增「折叠全部」—— 31 个芯片组全展开一屏装不下，一键收起比逐个点
        # 箭头快得多（参照 asus_bios_checker v2.2.0 的同名功能）。
        self.btn_cat_collapse = tk.Button(lhead, text="折叠全部", font=FONT_SS,
                                          bg=C_CARD, fg=C_SUB,
                                          activebackground=C_BTN_HOVER,
                                          activeforeground=C_ACCENT_HOT,
                                          relief="flat", bd=0, padx=S(6), pady=S(0),
                                          cursor="hand2",
                                          command=self._toggle_collapse_all)
        self.btn_cat_collapse.pack(side="right", padx=(S(0), S(6)))
        self._bind_hover_fg(self.btn_cat_collapse, C_SUB, C_ACCENT_HOT)
        # v2.4.0：目录刷新按钮（原来必须进设置窗才能刷新，多两步操作）
        self.btn_cat_refresh = tk.Button(lhead, text="↻", font=FONT_B,
                                         bg=C_CARD, fg=C_SUB,
                                         activebackground=C_BTN_HOVER,
                                         activeforeground=C_ACCENT_HOT,
                                         relief="flat", bd=0, padx=S(6), pady=S(0),
                                         cursor="hand2",
                                         command=lambda: self._refresh_now(None))
        self.btn_cat_refresh.pack(side="right")
        self._bind_hover_fg(self.btn_cat_refresh, C_SUB, C_ACCENT_HOT)

        # 搜索框（v2.4.0 新增：实时过滤型号 / 芯片组）
        self._search_wrap = tk.Frame(lf, bg=C_CARD)
        self._search_wrap.grid(row=1, column=0, sticky="ew", pady=(S(10), S(6)))
        self.ent_search = tk.Entry(self._search_wrap, textvariable=self.v_search,
                                   font=FONT_S, bg=C_INSET, fg=C_DIM,
                                   insertbackground=C_TEXT, relief="flat", bd=0,
                                   highlightthickness=S(1),
                                   highlightbackground=C_BORDER,
                                   highlightcolor=C_ACCENT)
        # v2.2.1：字号调大后同步加高输入条；ipadx 5→3 让占位文字与标题同一条左边线
        self.ent_search.pack(fill="x", ipady=S(6), ipadx=S(3))
        self.v_search.set(SEARCH_PH)
        self.ent_search.bind("<FocusIn>", self._search_focus_in)
        self.ent_search.bind("<FocusOut>", self._search_focus_out)
        self.v_search.trace_add("write", self._on_search_changed)

        twrap = ttk.Frame(lf, style="Card.TFrame")
        # v2.2.1：去掉左侧 8px 内边距 —— 树内容与外层「主板目录」「目录更新」对齐
        twrap.grid(row=2, column=0, sticky="nsew", pady=(S(0), S(4)), padx=(S(0), S(0)))
        twrap.columnconfigure(0, weight=1)
        twrap.rowconfigure(0, weight=1)
        self.cat_tree = ttk.Treeview(twrap, show="tree", selectmode="browse",
                                     height=16, style="Cat.Treeview")
        # v2.1.1：列宽不再写死，改由 _auto_fit_cat() 按目录实测文本宽度自动设定
        #（v2.3.7 写死 300px 仍装不下 326px 的长型号名，右侧被裁）
        # stretch=False 是关键：Treeview 的列 stretch 默认为 1，控件当前宽度小于列宽时
        # Tk 会把可伸缩列压回控件宽度（且不低于 minwidth），使自适应结果立刻被打回。
        self.cat_tree.column("#0", width=S(CAT_TREE_INIT), minwidth=S(CAT_TREE_MIN),
                            stretch=False)
        self.cat_tree.grid(row=0, column=0, sticky="nsew")
        self.cat_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        # v2.5.5：目录为空时的占位（旧版这里是一个空木框 + 底部一行小字，
        # 首次启动那 1~3 秒看起来像"界面没做完"）。place 覆盖在树区域中央，
        # 不占布局位，目录一填进来就 place_forget。
        self._cat_ph = tk.Label(twrap, text="正在读取主板目录…", font=FONT_S,
                                bg=C_CARD, fg=C_DIM)
        self._cat_ph.place(relx=0.5, rely=0.32, anchor="center")
        # v2.2.0：记住手动展开的芯片组（重启后自动还原，常用芯片组不用每次重展）
        self.cat_tree.bind("<<TreeviewOpen>>", self._on_cat_open)
        self.cat_tree.bind("<<TreeviewClose>>", self._on_cat_open)
        cys = ttk.Scrollbar(twrap, orient="vertical", command=self.cat_tree.yview)
        cys.grid(row=0, column=1, sticky="ns")
        self.cat_tree.configure(yscrollcommand=cys.set)
        # 说明：不加横向滚动条 —— Treeview 的裁切发生在**列内部**（文字超出列宽即被
        # 裁掉），xview 只能滚动到视口外的列，对列内裁切无效（实测 xview 恒为
        # (0,1)）。因此正确做法是让列宽足够，而不是加横滚条。
        # 窗口尺寸变化 → 右栏保底上限跟着变（实测值有缓存，重算很轻）
        self._body.bind("<Configure>", lambda _e: self._auto_fit_cols(), add="+")

        # 搜索无结果提示（v2.4.0）：目录里找不到时给一条去官网的出路
        self._nores = tk.Frame(lf, bg=C_CARD)
        self.lnk_site_search = tk.Label(self._nores, text="目录中未找到 → 去官网搜索 ↗",
                                        font=FONT_S, bg=C_CARD, fg=C_BLUE,
                                        cursor="hand2")
        self.lnk_site_search.pack(anchor="w", padx=(S(0), S(0)))
        self.lnk_site_search.bind("<Button-1>", lambda e: self._on_site_search())
        self._nores.grid(row=3, column=0, sticky="w", pady=(S(2), S(2)))
        self._nores.grid_remove()

        # v2.5.0：v_cat_upd 的**显示位置**挪到栏 2 的 footer（见 mfoot）；
        # 变量本身已提前到状态初始化处定义。

    def _ui_split_bars(self, body):
        """两条可拖拽分隔条（栏1|栏2、栏2|栏3），由 `_split_which` 区分在拖哪条。"""
        # ---------- v2.5.0 两条可拖拽分隔条（栏1|栏2、栏2|栏3）----------
        # 为什么自绘而不是 ttk.PanedWindow：PanedWindow 的 sash 样式来自系统主题，
        # 深色主题下是一条突兀的浅色槽，且它会把卡片收编成 pane（卡片样式、
        # 内边距、圆角都要重做）。自绘成本极低：一个 10px 透明命中区 + 1px 细线。
        # 细线本身有层级语义（"这里是可调的分界"），宽区保证鼠标好抓。
        # 两条分隔条共用一套逻辑，用 _split_which 记「正在拖哪一条」。
        self._split_which = 0
        self._split = self._make_split(body, 1, 0)      # 栏1 | 栏2
        self._split2 = self._make_split(body, 3, 1)     # 栏2 | 栏3

    def _ui_board_card(self, body):
        """栏 2：主板型号列表 + footer 计数（`v_cat` / `v_cat_upd` 都显示在这里）。"""
        # ===== 中：主板型号列表（v2.5.0）=====
        mf = self._card(body)
        mf.grid(row=0, column=2, sticky="nsew")
        mf.grid_propagate(False)
        mf.columnconfigure(0, weight=1)
        mf.rowconfigure(1, weight=1)
        self._mf = mf
        mhead = ttk.Frame(mf, style="Card.TFrame")
        mhead.grid(row=0, column=0, sticky="ew")
        ttk.Label(mhead, text="主板型号", style="H.TLabel").pack(side="left")
        self.v_board_n = tk.StringVar(value="")
        ttk.Label(mhead, textvariable=self.v_board_n, style="MonoSub.TLabel").pack(
            side="right")
        mwrap = tk.Frame(mf, bg=C_CARD)
        mwrap.grid(row=1, column=0, sticky="nsew", pady=(S(10), S(0)))
        # v2.5.0：中栏 footer —— 参照实现（asus v2.2.0）把「共 N 款 · 目录更新」
        # 放在这里。中栏 340px 横跨显示，比塞进 250px 的导航栏标题行宽裕得多。
        mfoot = ttk.Frame(mf, style="Card.TFrame")
        mfoot.grid(row=2, column=0, sticky="ew", pady=(S(8), S(0)))
        self._mfoot = mfoot
        self._lbl_cat = ttk.Label(mfoot, textvariable=self.v_cat,
                                  style="MonoSub.TLabel")
        self._lbl_cat.pack(side="left")
        self._lbl_cat_upd = ttk.Label(mfoot, textvariable=self.v_cat_upd,
                                      style="MonoDim.TLabel")
        self._lbl_cat_upd.pack(side="right")
        # v2.5.5：窄窗下 footer 装不下两段文字时分级让路（见 _fit_mfoot）
        mfoot.bind("<Configure>", self._fit_mfoot, add="+")
        mwrap.columnconfigure(0, weight=1)
        mwrap.rowconfigure(0, weight=1)
        self.board_tree = ttk.Treeview(mwrap, show="tree", selectmode="browse",
                                       height=16, style="Mod.Treeview")
        self.board_tree.grid(row=0, column=0, sticky="nsew")
        # v2.5.5：型号列表空占位（目录还没读到 / 没选芯片组时给一句下一步）
        self._board_ph = tk.Label(mwrap, text="正在读取主板目录…", font=FONT_S,
                                  bg=C_CARD, fg=C_DIM,
                                  wraplength=S(240), justify="center")
        self._board_ph.place(relx=0.5, rely=0.28, anchor="center")
        _bsb = ttk.Scrollbar(mwrap, orient="vertical", command=self.board_tree.yview)
        self.board_tree.configure(yscrollcommand=_bsb.set)
        _bsb.grid(row=0, column=1, sticky="ns")
        self.board_tree.bind("<<TreeviewSelect>>", self._on_board_select)
        # 型号名超出列宽时用悬停提示补全（栏2 不按 max 定宽的理由见常量区注释）
        self.board_tree.bind("<Motion>", self._on_board_motion)
        self.board_tree.bind("<Leave>", self._on_board_leave)
        self._hover_board = None
        self._tip = None

    def _ui_bios_card(self, body):
        """栏 3：BIOS 列表 —— 标题行、主板级提示、分组框、列表宿主、右键菜单。"""
        # ===== 右：BIOS 明细 =====
        rf = self._card(body)
        rf.grid(row=0, column=4, sticky="nsew")
        self._rf = rf
        # v2.4.0 关键修复：右栏改 grid 布局。grow/_panel_note_box/list_holder 都
        # 想放在 rf row=2，但 grid 不允许同 row 多 widget。
        # 解决：建一个 inner container 放 rf row=2 expand=True（占据 BIOS 列表主区），
        # grow/_panel_note_box/list_holder 改为 pack 进 container 内部（顺序可控）。
        # orow 在 rf row=4、pbar 在 rf row=5 固定行，不受 list_holder 影响。
        rf.columnconfigure(0, weight=1)
        # v2.5.5：列表行不再吃剩余高度（原 weight=1）。改为按内容行数定高，
        # 剩余高度交给卡片底部的弹性空行（row 7，无控件）。见 TV_ROWH 处注释。
        rf.rowconfigure(2, weight=0)
        # v2.5.0：详情按内容自撑（weight=0 + minsize）—— 说明越长详情越高，
        # 无需任何硬编码比例。
        rf.rowconfigure(4, weight=0, minsize=S(RIGHT_DETAIL_MIN))
        # 卡片底部的弹性空行：row 3 / 5 / 7 都没有控件，只靠 weight 吸收余量。
        # 放在最后一行的原因：让所有内容顶部对齐，空白只出现在卡片最下方。
        rf.rowconfigure(7, weight=1)
        # row 0: trow, row 1: brow, row 2: _list_zone (expand), row 3: 分隔线, row 4: drow, row 5: orow, row 6: pbar
        self._list_zone = ttk.Frame(rf, style="Card.TFrame")
        self._list_zone.grid(row=2, column=0, sticky="nsew", pady=(S(10), S(4)))

        # 型号标题行
        trow = ttk.Frame(rf, style="Card.TFrame")
        trow.grid(row=0, column=0, sticky="ew")
        self._title_row = trow
        # v2.3.1：**先** pack 右侧组。Tk 按 pack **调用顺序**分配空间 —— 右侧组
        # （打开官网按钮 + 数据源徽章）必须先于标题/副标题拿到宽度，否则空间不足
        # 时徽章会被压成 0 宽（实测 mapped=0 / w=6px / reqw=138px：文字在数据里
        # 但屏幕上一个像素都没有）。这样让路顺序才由"内容重要性"决定，
        # 而不是碰巧由 pack 的书写顺序决定。
        self._right_box = ttk.Frame(trow, style="Card.TFrame")
        self._right_box.pack(side="right", pady=(S(6), S(0)))
        # v2.3.6：Link 风格（背景=C_CARD 与主板卡同色，蓝色文字+↗ 外链箭头）
        self.btn_openpage = tk.Button(self._right_box, text="打开官网支持页  ↗",
                                      font=FONT_S, bg=C_CARD, fg=C_BLUE,
                                      activebackground=C_CARD,
                                      activeforeground=C_ACCENT_HOT,
                                      relief="flat", bd=0, cursor="hand2",
                                      padx=S(10), pady=S(4),
                                      command=self._on_open_site)
        self.btn_openpage.pack(side="right")
        self._bind_hover_fg(self.btn_openpage, C_BLUE, C_ACCENT_HOT)
        # 数据源徽章排在按钮左侧。它是**不可替代**的信息（当前读的是全球站还是
        # 中国站），所以永不参与让路；slug 才是可牺牲的补充信息。
        self.lbl_host = tk.Label(self._right_box, text="", font=FONT_SS,
                                 bg=C_CARD, fg=C_DIM)
        self.lbl_host.pack(side="right", padx=(S(0), S(10)))
        # v2.5.5：徽章也会让路（标题装不下时），见 _show_board_title 的三级顺序
        self._host_hidden = False
        self.v_board_title = tk.StringVar(value="请先在左侧选择主板型号")
        # v2.2.0：标题超长时按可用宽度省略（见 _show_board_title / _fit_board_title），
        # 否则长型号名会把右侧「打开官网支持页」挤出可视区
        self.lbl_board_title = ttk.Label(trow, textvariable=self.v_board_title,
                                         style="Board.TLabel", anchor="w")
        self.lbl_board_title.pack(side="left")
        # v2.3.1：副标题（slug）并入本行。原来是独立的一行 brow —— 标题区因此
        # 要占 45 + 26 + 15 = 86px 才到列表，其中一半是"两行标题"的行距。
        self._sub_box = ttk.Frame(trow, style="Card.TFrame")
        self._sub_box.pack(side="left", padx=(S(10), S(0)), pady=(S(9), S(0)))
        self.v_board_sub = tk.StringVar(value="")
        self.lbl_sub = ttk.Label(self._sub_box, textvariable=self.v_board_sub,
                                 style="Sub.TLabel")
        self.lbl_sub.pack(side="left")
        self._sub_hidden = False        # slug 槽当前是否被让路隐藏
        # v2.3.1：副标题内容变化也要重算让路。_enter_loading 的顺序是「先算标题、
        # 再 set slug」，而 <Configure> 不会因内部内容变化而触发 —— 不挂这个
        # trace，slug 撑宽后就没人再评估，标题会被挤到 178px（需要 322px）。
        self.v_board_sub.trace_add("write", lambda *_a: self._refit_title_soon())
        trow.bind("<Configure>", self._fit_board_title, add="+")

        # ---------- 主板级提示（官方 SOP / 升级须知 / YouTube 教程）
        self.v_panel_note = tk.StringVar(value="")
        self._panel_note_box = tk.Frame(self._list_zone, bg=C_BLUE_BG,
                                        highlightbackground="#33495c",
                                        highlightthickness=S(1))
        self._panel_note_lbl = tk.Label(self._panel_note_box, textvariable=self.v_panel_note,
                                        font=FONT_S, bg=C_BLUE_BG, fg="#a8c4dc",
                                        justify="left", wraplength=S(720), anchor="w")
        self._panel_note_lbl.pack(fill="x", padx=S(10), pady=S(6))
        self._panel_note_box.pack_forget()

        # BIOS 类型分组（通常只有 1 组，多组时才显示）
        # v2.4.0：grow 改放进 _list_zone，rf 用 grid 布局
        self.grow = ttk.Frame(self._list_zone, style="Card.TFrame")
        self.v_grp = tk.StringVar()
        self.grp_box = ttk.Combobox(self.grow, textvariable=self.v_grp, state="readonly",
                                    width=30, font=FONT_S)
        self.grp_box.pack(side="left")
        self.grp_box.bind("<<ComboboxSelected>>", self._on_group_changed)

        # ---------- 列表宿主（v2.4.0 结构修复）
        # 原来 Treeview 与空状态占位直接在 rf 里 pack/forget，重新 pack 时会被
        # 追加到 pack 顺序末尾 —— 列表会跑到下载区下方。改为固定宿主容器，
        # 只在其内部切换 Treeview / 占位，位置永远稳定。
        self._list_holder = ttk.Frame(self._list_zone, style="Card.TFrame")
        # v2.4.0：list_holder 在 _list_zone 内 expand=True（占据 _list_zone 剩余空间）
        self._list_holder.pack(fill="both", expand=True)

        cols = ("ver", "date", "size", "note")
        self.tv = ttk.Treeview(self._list_holder, columns=cols, show="headings",
                               selectmode="browse", height=12)
        self._tv_h = None          # 最近一次设定的可视行数（见 _fit_tv_height）
        self._refit_tv_pending = False
        for cid, txt, w, anchor in (
                ("ver", "版本", 168, "w"),
                ("date", "发布日期", 110, "center"),
                ("size", "大小", 92, "center"),
                ("note", "更新说明", 380, "w")):
            self.tv.heading(cid, text=txt)
            # v2.2.0：初始宽度补上 DPI 缩放（v2.1.0 漏网 —— 这四列一直是裸像素）；
            # 真实宽度随后由 _fit_tv_cols 按容器宽度按比例重算
            self.tv.column(cid, width=S(w), anchor=anchor, stretch=(cid == "note"))
        self.tv.pack(fill="both", expand=True)
        # v2.2.0：列宽随容器宽度按比例分配。旧版四列写死 168/110/92/380（合计 750），
        # 窗口收到最小尺寸（1100）时右栏内宽只剩约 656px，「更新说明」挤到 286px。
        self._list_holder.bind("<Configure>", self._fit_tv_cols, add="+")
        # v2.5.5：卡片高度变化时重算「放得下几行」（见 _fit_tv_height）
        rf.bind("<Configure>", self._fit_tv_height, add="+")
        self.tv.bind("<Double-1>", lambda e: self._on_tv_double_click())
        # v2.4.0：行 hover 高亮 + 右键菜单
        self.tv.bind("<Motion>", self._on_tv_motion)
        self.tv.bind("<Leave>", lambda e: self._clear_hover())
        # v2.5.0：栏 2 的型号悬停提示也要在鼠标离开时收掉
        self.board_tree.bind("<Destroy>", lambda e: self._hide_tip())
        self.tv.bind("<Button-3>", self._on_tv_menu)
        self._tv_menu = tk.Menu(self.root, tearoff=0, bg=C_CARD, fg=C_TEXT,
                                activebackground=C_SEL_BG, activeforeground=C_TEXT,
                                bd=0, font=FONT_S)
        self._tv_menu.add_command(label="复制版本号", command=self._menu_copy_ver)
        self._tv_menu.add_command(label="复制下载链接", command=self._menu_copy_url)
        self._tv_menu.add_separator()
        self._tv_menu.add_command(label="打开官网支持页", command=self._on_open_site)
        # 选中行变化 → 底部详情同步（v2.5.0）
        self.tv.bind("<<TreeviewSelect>>",
                     lambda _e: self._show_detail(self._selected_item()))
        return rf

    def _ui_detail_zone(self, rf):
        """选中版本详情凹槽：版本/日期/大小 + 复制链接 + 下载 + 说明 + SHA-256。"""
        # ---------- 选中版本详情（v2.5.0，参照 asus_bios_checker v2.2.0）
        # 为什么值得单独一块：表格把「说明」列让给宽度、只能显示一行且常被截断；
        # 详情区把同一个版本的完整信息摊平显示（不截断，最多 DETAIL_MAX_LINES 行），
        # 并把「复制下载链接 / 下载此版本」放在**手指已经落在这个版本上**的位置。
        # 底色取洼地 C_INSET —— 读作「嵌在卡片里的一块详情凹槽」，与表格体同族。
        self._detail_zone = tk.Frame(rf, bg=C_INSET,
                                     highlightbackground=C_BORDER,
                                     highlightthickness=S(1))
        self._detail_zone.grid(row=4, column=0, sticky="nsew", pady=(S(8), S(0)))
        self._detail_zone.columnconfigure(0, weight=1)
        self._det_item = None
        # 行 0：版本号 + 日期 + 大小 ....................... [复制下载链接] [下载此版本]
        drow = tk.Frame(self._detail_zone, bg=C_INSET)
        drow.grid(row=0, column=0, sticky="ew", padx=S(12), pady=(S(9), S(0)))
        drow.columnconfigure(3, weight=1)          # 中间的弹性空隙
        self._det_ver = tk.Label(drow, text="", font=FONT_B, bg=C_INSET, fg=C_TEXT)
        self._det_ver.grid(row=0, column=0, sticky="w")
        self._det_meta = tk.Label(drow, text="", font=FONT_MONO, bg=C_INSET, fg=C_SUB)
        self._det_meta.grid(row=0, column=1, sticky="w", padx=(S(10), S(0)))
        self._det_size = tk.Label(drow, text="", font=FONT_MONO, bg=C_INSET, fg=C_SUB)
        self._det_size.grid(row=0, column=2, sticky="w", padx=(S(12), S(0)))
        # v2.5.5：详情槽不再放第二个红色主按钮。
        # 原来这里「复制下载链接」(灰) + 「下载此版本」(红)，底部还有「下载选中版本」(红)
        # —— 同屏两个红按钮，而它们下的是**同一个文件**（详情槽显示的就是选中行）。
        # 红色预算按 v2.3.0 定下的规矩只给唯一主操作：底部那颗。这里降为次级灰按钮，
        # 复制链接再降一档为文字链（与「打开官网支持页 ↗」同族）。
        self.btn_det_url = tk.Button(drow, text="复制下载链接", font=FONT_S,
                                     bg=C_INSET, fg=C_BLUE,
                                     activebackground=C_INSET,
                                     activeforeground=C_ACCENT_HOT,
                                     relief="flat", bd=0,
                                     padx=S(10), pady=S(4), cursor="hand2",
                                     command=self._menu_copy_url)
        self.btn_det_url.grid(row=0, column=4, sticky="e")
        self.btn_det_dl = tk.Button(drow, text="下载此版本", font=FONT_S,
                                    bg=C_BTN, fg=C_TEXT,
                                    activebackground=C_BTN_HOVER,
                                    activeforeground=C_TEXT,
                                    relief="solid", bd=S(1),
                                    padx=S(14), pady=S(4), cursor="hand2",
                                    command=self._on_download)
        self.btn_det_dl.grid(row=0, column=5, sticky="e", padx=(S(10), S(0)))
        self._bind_hover_fg(self.btn_det_url, C_BLUE, C_ACCENT_HOT)
        self._bind_hover(self.btn_det_dl, C_BTN, C_BTN_HOVER)
        # 行 1：更新说明（不截断，最多 DETAIL_MAX_LINES 行；超出以「…」收尾）
        self._det_note = tk.Label(self._detail_zone, text="", font=FONT_S,
                                  bg=C_INSET, fg=C_DIM, anchor="w",
                                  justify="left", wraplength=S(600))
        self._det_note.grid(row=1, column=0, sticky="ew",
                            padx=S(12), pady=(S(6), S(0)))
        # 行 2：SHA-256（等宽 —— 这是最典型的"要逐位核对"的字符串）
        self._det_sha = tk.Label(self._detail_zone, text="", font=FONT_SS,
                                 bg=C_INSET, fg=C_DIM, anchor="w")
        self._det_sha.grid(row=2, column=0, sticky="ew",
                           padx=S(12), pady=(S(6), S(9)))
        # 换行宽跟随**详情面板**（不是标签自己）—— 否则会回到那个反馈环
        self._detail_zone.bind("<Configure>", self._on_detail_configure, add="+")
        self._show_detail(None)

    def _ui_empty_state(self):
        """列表空状态占位，同时覆盖「未选型号 / 查询中 / 无数据」三种语义。"""
        # ---------- 空状态占位（三种语义：未选型号 / 查询中 / 无数据）
        self._empty_box = tk.Frame(self._list_holder, bg=C_CARD)
        # v2.2.0：整块用 place 居中。旧版靠图标上方的固定 pady(40) 近似居上排布，
        # 窗口一拉高整块就明显偏上（下面留一大片空白），看着像没对齐。
        self._empty_inner = tk.Frame(self._empty_box, bg=C_CARD)
        self._empty_inner.place(relx=0.5, rely=0.45, anchor="center")
        self._empty_icon = tk.Label(self._empty_inner, text="◎",
                                    font=FONT_ICON,
                                    bg=C_CARD, fg=C_WATERMARK)
        self._empty_icon.pack(pady=(S(0), S(6)))
        self._empty_box_lbl1 = tk.Label(self._empty_inner, text="尚未选择主板型号",
                                        font=FONT_H, bg=C_CARD, fg=C_SUB)
        self._empty_box_lbl1.pack(pady=(S(0), S(8)))
        self._empty_box_lbl2 = tk.Label(self._empty_inner,
                                        text="在左侧主板目录里点选一款主板，"
                                             "或直接在搜索框输入型号关键字。\n"
                                             "BIOS 列表将显示在这里，并提供下载与 SHA-256 校验。",
                                        font=FONT_S, bg=C_CARD, fg=C_DIM,
                                        justify="center")
        self._empty_box_lbl2.pack()
        # v2.3.0：空状态给一个**明确的下一步动作**。旧版只有两行说明文字 ——
        # 用户第一次打开看到的是一块"死胡同"，不知道该干什么。
        self._empty_btn = tk.Button(self._empty_inner, text="去微星官网搜索  ↗",
                                    font=FONT_S, bg=C_BTN, fg=C_BLUE,
                                    activebackground=C_BTN_HOVER,
                                    activeforeground=C_ACCENT_HOT,
                                    relief="flat", bd=0, cursor="hand2",
                                    padx=S(16), pady=S(6),
                                    command=self._on_site_search)
        self._bind_hover(self._empty_btn, C_BTN, C_BTN_HOVER)
        self._show_empty(True)

    def _ui_download_row(self):
        """工具条行 0：保存目录（可点即打开）+ 选择 / 打开目录 / 取消 / 下载。"""
        # ---------- 下载区（v2.5.0：已升为跨三栏底部工具条，见 _abar）
        # 旧版这几行常驻在右卡片内部（占卡片高约 17%），且保存目录路径被 790px 的
        # 卡片挤到截断。现在容器换成窗口底部的 arow —— 控件本身与它们的 grid 列
        # 配置一行未动，只是换了 parent。
        # 注：右卡片原来的 row=3 分隔线与 row=4/5 两行随之空出（高度归零），
        # BIOS 列表（row=2, weight=1）自动接管全部释放的高度。
        orow = self._arow
        self._orow = orow
        # v2.0.0：操作行改用 grid + sticky="nsew" —— 同一 grid 行内的按钮会被
        # 拉到**同一行高**（= 最高的那个）。旧版用 pack，各按钮按自身字体行高
        # 排布：红主按钮（FONT_ACCENT -18px）比 Ghost 按钮（FONT_S -15px）高 7px，
        # 居中摆放后上下底边都差 3~4px，正是用户反馈的「上下没对齐」。
        # v2.3.1 列布局：0 目录路径（吸收剩余）1 弹性空隙 2 选择… 3 打开目录
        #                4 取消下载 5 下载选中版本
        # ⚠ v2.5.2 修正：上面这行注释一直写着「4 取消下载」，但源码把
        #   btn_cancel 也 grid 到了 **column 3**（与 btn_open_dir 同格）——
        #   实测后果：下载中两个按钮重叠 91px，「取消下载」盖掉「打开目录」92%，
        #   只漏出右侧 8px 一条边，且重叠区两个按钮都可点。已按注释的本意改回 4。
        # 间距口径见 BTN_GAP 常量：一律挂在**左元素的右 padx**。
        orow.columnconfigure(0, weight=1)
        # 左侧：保存目录路径。可点即打开（原来必须点「打开目录」按钮）；
        # 窄窗口下按可用宽度省略，见 _fit_dir_text —— Tk 的 Label 不会自己省略，
        # 它会撑大 grid 列把右侧按钮挤变形。
        self._dir_cell = ttk.Frame(orow, style="Card.TFrame")
        self._dir_cell.grid(row=0, column=0, sticky="w")
        self._dir_cap = ttk.Label(self._dir_cell, text="目录", style="Dim.TLabel")
        self._dir_cap.pack(side="left", padx=(S(0), S(6)))
        self.v_dir = tk.StringVar(value="")
        self._dir_full = ""        # 完整路径（显示值可能已被省略，不能拿它当原文）
        self.lnk_dir = tk.Label(self._dir_cell, textvariable=self.v_dir, font=FONT_S,
                                bg=C_CARD, fg=C_SUB, cursor="hand2", anchor="w")
        self.lnk_dir.pack(side="left")
        self.lnk_dir.bind("<Button-1>", lambda e: self._on_open_dir())
        self._bind_hover_fg(self.lnk_dir, C_SUB, C_BLUE)
        orow.bind("<Configure>", self._fit_dir_text, add="+")
        # 次级操作统一 Ghost 风格（深灰底 + 细边），与红主 / 蓝链形成三态
        self.btn_pick = tk.Button(orow, text="选择…", font=FONT_S,
                                  bg=C_BTN, fg=C_TEXT,
                                  activebackground=C_BTN_HOVER,
                                  activeforeground=C_TEXT,
                                  relief="solid", bd=S(1),
                                  padx=S(12), pady=S(5), cursor="hand2",
                                  command=self._on_pick_dir)
        self.btn_pick.grid(row=0, column=2, sticky="nsew", padx=(S(0), S(BTN_GAP)))
        self.btn_open_dir = tk.Button(orow, text="打开目录", font=FONT_S,
                                      bg=C_BTN, fg=C_TEXT,
                                      activebackground=C_BTN_HOVER,
                                      activeforeground=C_TEXT,
                                      relief="solid", bd=S(1),
                                      padx=S(12), pady=S(5), cursor="hand2",
                                      command=self._on_open_dir)
        self.btn_open_dir.grid(row=0, column=3, sticky="nsew", padx=(S(0), S(BTN_GAP)))
        # v2.0.0：取消下载（仅下载中显示，排在 打开目录 与 下载选中版本 之间）
        # v2.5.2：grid 列由 3 改为 4 —— 它原本与 btn_open_dir 挤在同一格。
        # 旧注释写「pack 顺序保证它在左侧」也早已脱节（v2.0.0 起这一行就是 grid）。
        self.btn_cancel = tk.Button(orow, text="取消下载", font=FONT_S,
                                    bg=C_BTN, fg=C_TEXT,
                                    activebackground=C_BTN_HOVER,
                                    activeforeground=C_ACCENT_HOT,
                                    relief="solid", bd=S(1),
                                    padx=S(12), pady=S(5), cursor="hand2",
                                    command=self._on_cancel_download)
        # 主操作：MSI 红（tk.Button，避开 vista 主题 ttk.Button 的 ■ 装饰）
        self.btn_dl = tk.Button(orow, text="下载选中版本", font=FONT_ACCENT,
                                bg=C_ACCENT_BTN, fg="#ffffff",
                                activebackground=C_ACCENT_BTN_HOT,
                                activeforeground="#ffffff",
                                disabledforeground=C_ACCENT_BTN_FG_DIS,
                                relief="flat", bd=0,
                                padx=S(18), pady=S(5), cursor="hand2",
                                command=self._on_download)
        self.btn_dl.grid(row=0, column=5, sticky="nsew")
        # 说明：btn_dl 的左 padx 保持 0 —— 间距由它左边那位（btn_open_dir 或
        # 下载中的 btn_cancel）的右 padx 提供，见 BTN_GAP 常量。
        for _b, _base, _hot in ((self.btn_pick, C_BTN, C_BTN_HOVER),
                                (self.btn_open_dir, C_BTN, C_BTN_HOVER),
                                (self.btn_cancel, C_BTN, C_BTN_HOVER),
                                (self.btn_dl, C_ACCENT_BTN, C_ACCENT_BTN_HOT)):
            self._bind_hover(_b, _base, _hot)

    def _ui_progress_row(self):
        """工具条行 1：自绘胶囊进度条 + 速度/剩余时间文案。"""
        # v2.5.0：进度行同样搬到窗口底部的 prow（同一工具条的第二行）
        pbar = self._prow
        self._pbar_row = pbar
        # v2.3.0：ttk.Progressbar → 胶囊自绘（理由见 PbarCanvas docstring）
        # width 必须显式给：Tk Canvas 的默认请求宽是 **10cm ≈ 378px**，不收敛的话
        # pack 会把右侧文案标签压到 309px（需要 391px）→ 文案被裁成 "...(57"。
        # 本控件走 expand=True，真实宽度由容器决定；请求值只决定"空间不够时谁先让步"。
        self.pb = PbarCanvas(pbar, maximum=100, value=0,
                             width=S(60), height=S(PB_H),
                             bg=C_CARD, bd=0, highlightthickness=0)
        self.pb.pack(fill="x", side="left", expand=True)
        self.pb.set_idle(True)     # v2.5.5：启动即隐形，见 PbarCanvas.set_idle
        self.v_pb = tk.StringVar(value="")
        # v2.4.0：width 30→46 —— 原 30 字符格装不下完整文案，被裁成「(4...」
        # v2.2.0：窄窗口自动压成短文案（见 _fit_progress_text / _dl_progress）
        # v2.2.2：字符格不再写死，按上界样例实测宽度换算（默认 43 字符格），既让
        # 默认 1200×780 能显示完整文案，又把省下的宽还给进度条本身
        self.lbl_pb = ttk.Label(pbar, textvariable=self.v_pb, style="Pb.TLabel",
                                width=self._pb_label_chars(False), anchor="e")
        self.lbl_pb.pack(side="left", padx=(S(12), S(0)))
        self._pb_compact = False
        pbar.bind("<Configure>", self._fit_progress_text, add="+")

    def _ui_toast(self, rf):
        """结果横幅：下载完成或失败的即时反馈，默认隐藏，由 `_toast_show` 唤出。"""
        # 结果横幅（v2.4.0）：下载完成 / 失败的即时反馈，不必等弹窗
        # v2.0.0 修复：右栏 rf 的子控件全部走 grid，旧版这里用 pack 显示，
        # TclError 被 except 吞掉 —— 横幅其实从未真正显示过。
        self._toast = tk.Frame(rf, bg=C_OK_BG,
                               highlightbackground=C_OK_BORDER,
                               highlightthickness=S(1))
        self._toast_lbl = tk.Label(self._toast, text="", font=FONT_S, bg=C_OK_BG,
                                   fg=C_OK, anchor="w", justify="left", wraplength=S(760))
        self._toast_lbl.pack(fill="x", padx=S(12), pady=S(7))

    def _ui_finish(self):
        """收尾：关窗协议（保存几何与展开状态）+ 启动即显示实际保存目录。"""
        # v2.2.0：关窗时保存窗口几何与目录树展开状态（见 _on_close）
        # v2.5.4：拆分后这里原本写的是裸 `root`（旧 _build_ui 的局部变量），
        # 会抛 NameError 并被下面的 except 吞掉 —— 协议静默失效、关窗不再存盘。
        # 统一走 self.root；`_p_v254_uistruct.py` 现在会断言该协议确实已绑定。
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass
        # 启动即显示实际保存目录（旧版这里是空白，用户不知道文件会存到哪）
        self._set_dir_display(self._default_dir())
        # v2.5.5：建完再同步一次主按钮状态。
        # 详情槽（_ui_detail_zone）比底部工具条（_ui_download_row）先建，
        # 它内部那次 _sync_dl_btn() 拿到的是"btn_dl 还不存在"，只会在日志里留一行；
        # 这里补上首帧的启用态，否则空态下主按钮是亮红可点的。
        self._sync_dl_btn()

    # ------------------------------------------------------------- 辅助
    def _set_status(self, msg, kind="info"):
        """排队一条状态消息。kind 决定状态点颜色：info / run / ok / err / warn。"""
        self.q.put(("status", msg, kind))

    def _ui_status(self, msg, kind="info"):
        self.v_status.set(msg)
        color = {"run": C_AMBER, "ok": C_OK, "err": C_ACCENT_HOT,
                 "warn": C_AMBER}.get(kind, C_DIM)
        self._dot_base = color
        try:
            self.dot_status.configure(fg=color)
        except Exception:
            pass
        # v2.3.0：长任务里状态点"呼吸"，一眼就能看出"还在动"
        self._dot_pulse(kind == "run")

    def _dot_pulse(self, on):
        """状态点呼吸（v2.3.0）。

        旧版状态点只有一个静态颜色 —— 目录抓取、下载这类长任务进行中，界面看起来
        和卡死没有区别。现在用 ζ=0.9 的弹簧在 0↔1 之间来回驱动颜色，靠 on_done
        链式重启；任务结束立刻收敛回常态色（不是"停在半亮"，那是残影）。
        """
        if not on:
            self._dot_on = False
            self.anim.cancel("dotp")
            try:
                self.dot_status.configure(fg=self._dot_base)
            except Exception:
                pass
            return
        if self._dot_on:
            return                              # 已在呼吸中，别叠加第二条链
        self._dot_on = True

        def _frame(x, v):
            try:
                self.dot_status.configure(
                    fg=_lerp_color(C_AMBER, C_ACCENT_HOT,
                                   max(0.0, min(1.0, x))))
            except Exception:
                pass

        def _cycle():
            if not self._dot_on:
                return
            cur = self.anim.spring_x("dotp")
            self.anim.spring("dotp", SPR_PULSE, _frame,
                             0.0 if (cur or 0.0) > 0.5 else 1.0,
                             on_done=_cycle)

        _cycle()

    # ------------------------------------------------------------- 动效原语
    def _bind_states(self, w, base, hot, prop="bg", enabled_check=False):
        """可交互控件的统一**状态层**（v2.3.0）。

        三个通道，各自解决一个旧版手感问题：
          H（hover，弹簧 SPR_VALUE）—— 旧版同 key 的 run() 是"从 0 重新计时"，
             鼠标快速进/出时颜色会先跳回起点再走一遍，肉眼可见。弹簧 retarget
             保留当前值与速度 → 反向是**连续回摆**，不再跳。
          P（按下深度，弹簧 SPR_PRESS）—— **按下即反馈**：ButtonPress 当帧就到 1.0
             （Apple：不在抬起后才响应）；ButtonRelease 用 ζ=0.7 的欠阻尼弹簧回弹，
             带一点点弹跳，像真的"按下去又弹起来"。
          禁用态 —— 按下/悬停都不改色。

        配色合成：`lerp(base, hot, H)` 之后再朝黑混 `PRESS_DARKEN*P`，两层互不覆盖。
        """
        kh = ("H", prop, id(w))
        kp = ("P", prop, id(w))
        st = {"press": False}

        def _render():
            try:
                if enabled_check and str(w.cget("state")) == "disabled":
                    return
                h = self.anim.spring_x(kh) or 0.0
                p = self.anim.spring_x(kp) or 0.0
                col = _lerp_color(base, hot, max(0.0, min(1.0, h)))
                p = max(0.0, min(1.0, p))
                if p > 0.004:
                    col = _mix(col, "#000000", PRESS_DARKEN * p)
                w.configure(**{prop: col})
            except Exception:
                pass

        def _frame(_x, _v):
            _render()

        def _enter(_e=None):
            self.anim.spring(kh, SPR_VALUE, _frame, 1.0)

        def _leave(_e=None):
            st["press"] = False
            self.anim.spring(kh, SPR_VALUE, _frame, 0.0)

        def _down(_e=None):
            st["press"] = True
            # value=target=1.0 ⇒ 创建即静止：当帧立刻到位（"按下即反馈"）
            self.anim.spring(kp, SPR_PRESS, _frame, 1.0, value=1.0)

        def _up(_e=None):
            if not st["press"]:
                return
            st["press"] = False
            self.anim.spring(kp, SPR_PRESS, _frame, 0.0)

        w.bind("<Enter>", _enter, add="+")
        w.bind("<Leave>", _leave, add="+")
        w.bind("<ButtonPress-1>", _down, add="+")
        w.bind("<ButtonRelease-1>", _up, add="+")
        _render()

    def _bind_hover(self, btn, base, hot, dur=None):
        """tk.Button 背景状态层（hover 弹簧 + 按下即时反馈）。dur 仅保留兼容。"""
        self._bind_states(btn, base, hot, "bg", enabled_check=True)

    def _bind_hover_fg(self, lbl, base, hot, dur=None):
        """tk.Label（当链接用）前景色状态层。"""
        self._bind_states(lbl, base, hot, "fg")

    def _apply_row_colors(self, p):
        """按淡入进度 p（0~1，已是缓动后的值）刷新列表行 tag 配色。

        v2.3.0：曲线由调用方（弹簧）负责，这里只做 clamp —— 旧版内部再套一层
        _ease_out，等于把曲线算两遍，起步会"二次加速"，看起来像闪了一下。
        """
        e = max(0.0, min(1.0, p))
        try:
            # ⚠ 这里的调用顺序**不影响**优先级 —— tag 在 __init__ 里创建时就已定序，
            # tag_configure 对已存在的 tag 是原地改值，不会改变创建序。
            # 这里之所以也按 latest → row 书写，只是为了与创建处的顺序保持一致，
            # 免得后来人误以为"照这个顺序改就能调整优先级"（真正的规则见 __init__ 注释）。
            self.tv.tag_configure("latest",
                                  background=_lerp_color(C_CARD, C_GREEN_BG, e),
                                  foreground=_lerp_color(C_CARD, C_GREEN, e))
            self.tv.tag_configure("row", foreground=_lerp_color(C_CARD, C_TEXT, e))
            self.tv.tag_configure("rowh",
                                  background=_lerp_color(C_CARD, C_ROW_HOVER, e),
                                  foreground=_lerp_color(C_CARD, C_TEXT, e))
            self.tv.tag_configure("latest_h",
                                  background=_lerp_color(C_CARD, C_LATEST_HOVER, e),
                                  foreground=_lerp_color(C_CARD, C_GREEN, e))
        except Exception:
            pass

    def _fade_list_in(self):
        """切换型号后 BIOS 列表淡入（v2.3.0：定时缓出 → 弹簧 SPR_ENTER）。"""
        self._apply_row_colors(0.0)
        self.anim.spring("listfade", SPR_ENTER,
                         lambda x, v: self._apply_row_colors(x), 1.0, value=0.0)

    def _pb_set(self, target, dur=None):
        """进度条补间（v2.3.0：定时缓出 → 弹簧，速度连续）。

        旧版每次新进度都「从当前显示值重新起算一条缓出曲线」：每次回调速度归零，
        连续喂进度时表现为一顿一顿的"追不上"。弹簧的 retarget 保留速度，
        连续喂目标即是**匀速跟手**；ζ=1.0 保证绝不越过 100%。
        """
        try:
            cur = float(self.pb["value"])
        except Exception:
            cur = 0.0
        target = max(0.0, min(100.0, float(target)))
        self.anim.spring(
            "pb", SPR_VALUE,
            lambda x, v: self._pb_paint(max(0.0, min(100.0, x))),
            target, value=cur)

    def _pb_paint(self, v):
        try:
            self.pb.configure(value=v)
        except Exception:
            pass

    def _pb_flash(self, c_from, c_to, dur=None):
        """完成脉冲：配色红 → 绿（v2.3.0：定时缓出 → 弹簧，收尾带一点"落定"的力）。

        ζ=0.85 的过冲约 1.5%（被 clamp 到 1.0），换来的是尾巴上那一下"咔哒"——
        这正是 Apple 说的"给操作一个物理结论"，比匀速渐变更像"事情办完了"。
        """
        self.anim.spring("pbf", SPR_PULSE,
                         lambda x, v: self._pb_fill_at(c_from, c_to, x),
                         1.0, value=0.0)

    def _pb_fill_at(self, c_from, c_to, t):
        t = max(0.0, min(1.0, t))
        col = _lerp_color(c_from, c_to, t)
        try:
            if hasattr(self.pb, "set_fill"):
                self.pb.set_fill(col)
            else:
                self.st.configure("TProgressbar", background=col, lightcolor=col)
        except Exception:
            pass

    def _pb_settle(self):
        """下载完成 1.4s 后收尾：配色复位 + 进度条收回（v2.5.5）。

        先让用户看清 100% 那一帧，再收回去；顺序不能反 —— 反过来会看到
        「满格突然变空」的跳变。
        """
        self._pb_color_reset()
        self.pb.set_idle(True)

    def _pb_color_reset(self):
        try:
            if hasattr(self.pb, "set_fill"):
                self.pb.set_fill(C_ACCENT)
            else:
                self.st.configure("TProgressbar", background=C_ACCENT,
                                  lightcolor=C_ACCENT_HOT, darkcolor=C_ACCENT_DEEP)
        except Exception:
            pass

    def _status_flash(self, color, times=3):
        """状态栏文字闪烁（完成 / 失败的注意力提示）。

        v2.3.0：三角波（`abs(((p*n*2) % 2) - 1)`）改成弹簧链 —— 三角波在折返点
        是**速度突变**（尖角），看起来是"硬闪"；弹簧链每次折返都自然减速再加速，
        闪几次后停在常态色，不会像旧版那样在最后一刻还在满幅折返。
        """
        state = {"n": 0}

        def _frame(x, v):
            try:
                self.lbl_status.configure(
                    fg=_lerp_color(C_STATUS_FG, color,
                                   max(0.0, min(1.0, x))))
            except Exception:
                pass

        def _cycle():
            state["n"] += 1
            if state["n"] >= times * 2:
                self.anim.cancel("statusflash")
                try:
                    self.lbl_status.configure(fg=C_STATUS_FG)
                except Exception:
                    pass
                return
            self.anim.spring("statusflash", SPR_PULSE, _frame,
                             1.0 if state["n"] % 2 == 1 else 0.0,
                             on_done=_cycle)

        self.anim.spring_drop("statusflash")
        self._status_flash_n = state
        _cycle()

    def _shake_search(self):
        """搜索无结果时的横向回摆（v2.3.0：方波 → 欠阻尼弹簧 + 软边界）。

        旧版用 `int(p*6) % 2` 造方波：位移在 ±幅度之间**硬折返**，到最后一刻还在满幅
        跳变，看起来是"卡顿"而不是"抖动"。现在给弹簧一个初速度、目标是 0，
        ζ=0.55 自然衰减出 2~3 次来回且**必然收敛**；越界由 _soft_clamp 渐进吸收。
        """
        amp = S(9)
        cap = S(11)                      # 设计幅度内的位移 1:1 跟随，超出才软化
        try:
            self._search_wrap.grid_configure(padx=(-amp, 0))
        except Exception:
            pass
        self.anim.spring(
            "shake", SPR_SHAKE,
            lambda x, v: self._shake_frame(x, cap),
            0.0, value=-amp,
            velocity=_kick_velocity(amp * 0.85, *SPR_SHAKE))

    def _shake_frame(self, x, cap):
        """把弹簧位移写进搜索框左内边距（软边界：界内 1:1，越界渐进吸收）。"""
        try:
            self._search_wrap.grid_configure(padx=(int(round(_soft_clamp(x, cap))), 0))
        except Exception:
            pass

    def _toast_show(self, text, ok=True, ttl=7000):
        """底部结果横幅：下载结果的即时反馈（自动隐藏，不必等弹窗）。

        v2.3.0：补上**入场过渡**并让出入场走同一条路径（对称）——旧版是"瞬间出现、
        瞬间消失"，一条横幅凭空闪现又凭空消失，是最廉价的那种动效。现在从下方
        S(14) 处按 Apple sheet 参数（ζ=0.8 / response 0.3）滑入，文字同时由底色
        渐显，出场反向滑回原位。
        """
        bg = C_OK_BG if ok else C_RED_BG
        bd = C_OK_BORDER if ok else "#7a2a2e"
        fg = C_OK if ok else "#ff9b95"
        try:
            self._toast.configure(bg=bg, highlightbackground=bd)
            self._toast_lbl.configure(text=text, bg=bg)
            self._toast_fg = fg
            if not self._toast.winfo_manager():
                self._toast.grid(row=6, column=0, sticky="ew",
                                 pady=(S(8) + TOAST_TRAVEL, S(0)))
            # 起表前先摆到"收起"位：否则 grid 与第一帧之间会露一帧旧字色
            self._toast_frame(0.0)
        except Exception:
            return
        if self._toast_job:
            try:
                self.root.after_cancel(self._toast_job)
            except Exception:
                pass
        self.anim.cancel("toastout")
        self.anim.spring("toastin", SPR_BANNER,
                         lambda x, v: self._toast_frame(x), 1.0, value=0.0)
        self._toast_job = self.root.after(ttl, self._toast_hide)

    def _toast_frame(self, t):
        """t∈[0,1]：0 = 收起（下移 + 只有底色），1 = 完全展开（原位 + 目标字色）。"""
        t = max(0.0, min(1.0, t))
        try:
            self._toast.grid_configure(
                pady=(S(8) + int(round(TOAST_TRAVEL * (1.0 - t))), 0))
            self._toast_lbl.configure(
                fg=_lerp_color(self._toast_lbl.cget("bg"), self._toast_fg, t))
        except Exception:
            pass

    def _toast_hide(self, animate=True):
        """隐藏横幅：先播出场（与入场同路径反向），动画结束再真正 grid_remove。"""
        self._toast_job = None
        if not animate or not _motion_enabled():
            try:
                if self._toast.winfo_manager():
                    self._toast.grid_remove()
            except Exception:
                pass
            return
        self.anim.cancel("toastin")
        self.anim.spring(
            "toastout", SPR_BANNER, lambda x, v: self._toast_frame(x), 0.0,
            value=self.anim.spring_x("toastin") or 0.0,
            on_done=self._toast_unmount)

    def _toast_unmount(self):
        try:
            if self._toast.winfo_manager():
                self._toast.grid_remove()
        except Exception:
            pass

    # ------------------------------------------------------------- 查询中加载态
    def _start_loading(self, title, sub="正在从微星官网读取 BIOS 列表…"):
        self._loading_name = title
        self._empty_box_lbl1.configure(text=title, fg=C_SUB)
        self._empty_box_lbl2.configure(text=sub)
        self._show_empty(True, keep_anim=True)
        self._loading_ticks = 0
        if self._loading_job is None:
            self._loading_job = self.root.after(320, self._loading_step)

    def _loading_step(self):
        self._loading_job = None
        if self._loading_name is None or not self._empty_box.winfo_manager():
            return
        self._loading_ticks = (self._loading_ticks + 1) % 4
        try:
            self._empty_box_lbl1.configure(
                text="正在查询 %s%s" % (self._loading_name, "·" * self._loading_ticks))
            self._empty_icon.configure(
                fg=(C_ACCENT_DEEP, C_ACCENT, C_ACCENT_HOT, C_ACCENT)[self._loading_ticks])
        except Exception:
            return
        self._loading_job = self.root.after(320, self._loading_step)

    def _stop_loading(self):
        self._loading_name = None
        if self._loading_job is not None:
            try:
                self.root.after_cancel(self._loading_job)
            except Exception:
                pass
            self._loading_job = None
        try:
            self._empty_icon.configure(fg=C_WATERMARK)
        except Exception:
            pass

    def _show_empty(self, on, title=None, sub=None, keep_title=False, keep_anim=False):
        """BIOS 列表为空时显示占位提示。

        切换发生在固定宿主容器 _list_holder 内部 —— 位置永远稳定
        （旧实现直接 pack/forget Treeview，重新 pack 会被追加到顺序末尾，
        列表会掉到下载区下方）。

        keep_title=True：型号已选定但无可用数据，占位显示型号名与原因，
        不重置标题区 / cur_slug（保留「打开官网支持页」能力）。
        keep_anim=True：查询中加载态，只切显示，不改任何文案。
        """
        if on:
            if self.tv.winfo_manager():
                self.tv.pack_forget()
            self._list_fill(True)      # v2.5.5：占位块吃满卡片
            if not self._empty_box.winfo_manager():
                self._empty_box.pack(fill="both", expand=True)
            # 主动作按钮只在"还没选型号"时出现；加载中 / 已选型号但无数据时收起
            # （那两种状态下"去官网搜索"不是下一步该做的事）
            try:
                if title is None and not keep_anim:
                    if not self._empty_btn.winfo_manager():
                        self._empty_btn.pack(pady=(S(16), S(0)))
                else:
                    self._empty_btn.pack_forget()
            except Exception:
                pass
            # 只丢弃残留的旧 status 消息（避免占位后被旧状态覆盖）；
            # busy/board/dl 等关键消息放回队列，绝不丢失
            kept = []
            try:
                while True:
                    m = self.q.get_nowait()
                    if m[0] != "status":
                        kept.append(m)
            except queue.Empty:
                pass
            for m in kept:
                self.q.put(m)
            if keep_anim:
                return
            self._stop_loading()
            if keep_title:
                self._empty_icon.configure(fg=C_WATERMARK)
                self._empty_box_lbl1.configure(text=title or "该型号暂无可用数据", fg=C_SUB)
                self._empty_box_lbl2.configure(text=sub or "")
            else:
                self._empty_icon.configure(fg=C_WATERMARK)
                self._empty_box_lbl1.configure(text="尚未选择主板型号", fg=C_SUB)
                self._empty_box_lbl2.configure(
                    text="在左侧主板目录里点选一款主板，"
                         "或直接在搜索框输入型号关键字。\n"
                         "BIOS 列表将显示在这里，并提供下载与 SHA-256 校验。")
                # 同时复位主板标题区，保持与空状态一致
                self._show_board_title("请先在左侧选择主板型号")
                self.v_board_sub.set("")
                self.lbl_host.configure(text="")
                self.cur_slug = None
                self.cur_items = []
                self._latest_iids = set()
                self._ui_status("就绪 · 请在左侧选择一款主板型号", "info")
        else:
            self._stop_loading()
            self._list_fill(False)     # v2.5.5：列表按行数定高，余量沉到卡片底部
            if self._empty_box.winfo_manager():
                self._empty_box.pack_forget()
            if not self.tv.winfo_manager():
                self.tv.pack(fill="both", expand=True)
            self._sync_dl_btn()        # v2.5.5：回到空态/无选中时主按钮同步禁用

    def _set_inflight(self, delta):
        """在途任务计数（v2.2.0）：计数归零才解除主按钮禁用。

        后台线程发 ("busy", True/False) 成对出现；目录抓取与型号查询可能重叠
        （目录过期自动刷新时用户仍可点型号），布尔标记会让先结束者错误解禁。
        """
        self._inflight = max(0, self._inflight + delta)
        self._busy(self._inflight > 0)

    def _busy(self, on):
        """查询 / 下载中禁用主按钮（tk.Button 用 config(state=...) 切换）。

        v2.5.5：这里不再直接写配色，只维护「在途」标记，状态与文案统一由
        `_sync_dl_btn()` 算 —— 否则"下载完解禁"会把"没选中"的禁用态又打开。
        """
        # 先掐掉进行中的 hover 渐变：否则动画帧会把 disabled 底色覆盖回去
        self.anim.cancel(("hb", id(self.btn_dl)))
        self._busy_flag = bool(on)
        self._sync_dl_btn()

    def _set_downloading(self, on):
        """下载态切换：主按钮禁用 + 显示「取消下载」；结束后隐藏并还原。"""
        self._busy(on)
        try:
            if on:
                self.btn_cancel.config(state=tk.NORMAL, bg=C_BTN)
                if not self.btn_cancel.winfo_manager():
                    # v2.5.2：column 3 -> 4（原与 btn_open_dir 同格，实测重叠 91px）
                    self.btn_cancel.grid(row=0, column=4, sticky="nsew",
                                         padx=(S(0), S(BTN_GAP)))
            elif self.btn_cancel.winfo_manager():
                self.btn_cancel.grid_remove()
        except Exception:
            pass

    # ------------------------------------------------------------- 搜索 / 快捷键
    def _search_value(self):
        """搜索框有效内容（占位文案显示中时视为空）。"""
        if self._search_ph:
            return ""
        return (self.v_search.get() or "").strip()

    def _search_focus_in(self, _ev=None):
        if self._search_ph:
            self._search_ph = False
            self.v_search.set("")
            try:
                self.ent_search.configure(fg=C_TEXT)
            except Exception:
                pass

    def _search_focus_out(self, _ev=None):
        if not (self.v_search.get() or "").strip():
            self._search_ph = True
            self.v_search.set(SEARCH_PH)
            try:
                self.ent_search.configure(fg=C_DIM)
            except Exception:
                pass

    def _on_search_changed(self, *_a):
        """输入即过滤（140ms 防抖，避免逐字符重建目录树）。"""
        if self._search_ph:
            return
        if self._search_job is not None:
            try:
                self.root.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.root.after(140, self._apply_search)

    def _apply_search(self):
        self._search_job = None
        q = self._search_value().lower()
        if q == self._search_q:
            return
        self._search_q = q
        self._populate_tree()
        if q and self._search_hits == 0:
            self._shake_search()
            self._set_status(
                "目录中未找到「%s」—— 可点左侧「去官网搜索」查已停售型号"
                % self._search_value(), "warn")

    def _on_site_search(self):
        """目录无命中时的出路：跳到微星官网站内搜索（覆盖已停售型号）。"""
        q = self._search_value()
        if q:
            webbrowser.open(BASE + "/search?q=" + urllib.parse.quote(q))
        else:
            webbrowser.open(BASE + "/Motherboards/Products")

    def _bind_shortcuts(self):
        r = self.root

        def _focus_search(_e=None):
            self.ent_search.focus_set()
            self.ent_search.select_range(0, "end")
            return "break"

        def _refresh(_e=None):
            self._refresh_now(None)
            return "break"

        def _dl(_e=None):
            self._on_download()
            return "break"

        r.bind("<Control-f>", _focus_search)
        r.bind("<Control-F>", _focus_search)
        r.bind("<F5>", _refresh)
        r.bind("<Escape>", self._on_escape)
        self.tv.bind("<Return>", _dl)
        self.ent_search.bind("<Return>", self._on_search_enter)

    def _on_escape(self, _ev=None):
        """Esc：清空搜索并回到完整目录。"""
        if self._search_value():
            self._search_ph = False
            self.v_search.set("")
            try:
                self.ent_search.configure(fg=C_TEXT)
            except Exception:
                pass
            self._search_q = ""
            self._populate_tree()
            self.root.focus_set()
            self._set_status("已清空搜索，显示完整目录")
            return "break"
        return None

    def _on_search_enter(self, _ev=None):
        """搜索框回车：跳到第一个命中型号并加载 BIOS 列表。"""
        for p in self.cat_tree.get_children():
            for c in self.cat_tree.get_children(p):
                bs = self.cat_tree.get_children(c)
                if bs:
                    self.cat_tree.item(p, open=True)
                    self.cat_tree.item(c, open=True)
                    self.cat_tree.selection_set(bs[0])
                    self.cat_tree.see(bs[0])
                    self._on_tree_select()
                    return "break"
        return "break"

    # ------------------------------------------------------------- 列表 hover / 右键
    def _on_tv_motion(self, ev):
        iid = self.tv.identify_row(ev.y)
        if iid == self._hover_row:
            return
        self._set_hover(iid)

    def _set_hover(self, iid):
        prev = self._hover_row
        if prev and prev != iid:
            try:
                self.tv.item(prev, tags=("latest", "row")
                             if prev in self._latest_iids else ("row",))
            except Exception:
                pass
        self._hover_row = iid or None
        if iid:
            try:
                self.tv.item(iid, tags=("latest_h",)
                             if iid in self._latest_iids else ("rowh",))
            except Exception:
                pass

    def _clear_hover(self):
        self._set_hover(None)

    def _on_tv_menu(self, ev):
        iid = self.tv.identify_row(ev.y)
        if not iid:
            return
        self.tv.selection_set(iid)
        self.tv.focus(iid)
        self._set_hover(iid)
        try:
            self._tv_menu.tk_popup(ev.x_root, ev.y_root)
        finally:
            try:
                self._tv_menu.grab_release()
            except Exception:
                pass

    def _clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text or "")
            self._set_status("已复制到剪贴板：%s" % (text or "")[:70], "ok")
        except Exception as e:
            _log("clipboard err %r" % (e,))

    def _menu_copy_ver(self):
        it = self._selected_item()
        if it:
            self._clipboard(clean_version(it.get("download_version")))

    def _menu_copy_url(self):
        it = self._selected_item()
        if it:
            self._clipboard(it.get("download_url") or "")

    def _poll_queue(self):
        """主线程消息泵：把后台线程的队列消息派发到 UI。

        v2.0.0：间隔自适应 —— 有消息（查询 / 下载中）时 60ms 保证进度顺滑，
        空闲时放宽到 160ms，减少无谓唤醒。
        """
        got = 0
        try:
            while True:
                m = self.q.get_nowait()
                self._dispatch(m)
                got += 1
        except queue.Empty:
            pass
        self.root.after(60 if got else 160, self._poll_queue)

    def _apply_dark_titlebar(self):
        """Windows 10 2004+ / 11：让 DWM 标题栏跟随内容明暗。

        本工具是深色皮肤（TITLEBAR_DARK=True）→ 传 1 开启沉浸式深色标题栏，
        与内容浑然一体；若换成浅色皮肤必须传 0，否则会出现「深色标题栏 +
        浅色内容」的视觉割裂。
        """
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            # DWMWA_USE_IMMERSIVE_DARK_MODE：20 (Win10 2004+) / 19 (老 build)
            # 取值由 TITLEBAR_DARK 控制（本工具深色主题 = 1 开启）
            for attr in (20, 19):
                val = ctypes.c_int(1 if TITLEBAR_DARK else 0)
                ok = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
                if ok == 0:  # S_OK
                    return
        except Exception:
            pass

    def _dispatch(self, m):
        kind = m[0]
        try:
            if kind == "status":
                self._ui_status(m[1], m[2] if len(m) > 2 else "info")
            elif kind == "busy":
                self._set_inflight(1 if m[1] else -1)
            elif kind == "cat_prog":
                self._cat_progress(m[1])
            elif kind == "catalog":
                self._apply_catalog(m[1], m[2])      # (catalog, err)
            elif kind == "board":
                self._apply_board(m[1])              # (slug,title,groups,note,err)
            elif kind == "dl_progress":
                self._dl_progress(*m[1])
            elif kind == "dl_done":
                self._dl_done(*m[1])
            elif kind == "err":
                messagebox.showerror(APP_TITLE, m[1], parent=self.root)
            elif kind == "info":
                messagebox.showinfo(APP_TITLE, m[1], parent=self.root)
        except Exception as e:
            _log("dispatch err %s: %r" % (kind, e))

    # ------------------------------------------------------------- 目录
    def _boot(self):
        cat, age = load_catalog_cached()
        if cat is not None:
            self.catalog = cat
            self.cat_updated = cat.get("updated", "")
            self._populate_tree()
            days = int(self.cfg.get("refresh_days") or 0)
            if days > 0 and age >= days * 86400:
                self._set_status("目录已过期（缓存 %d 天 > 设置的 %d 天），稍后自动刷新…"
                                 % (age // 86400, days))
                # v2.2.0：启动期自动刷新加随机延时。同一批装的机器常常在同一时刻
                # 开机并启动本工具，固定时刻刷新会让上游看到同步的请求尖峰。
                self.root.after(random.randint(400, 4000), self._start_catalog)
            else:
                hrs = max(0, int(age // 3600))
                tip = "不自动刷新" if days <= 0 else "每 %d 天自动检查" % days
                self._set_status("目录已就绪（缓存 %d 小时 · %s），请选择主板型号" % (hrs, tip))
        else:
            self._set_status("首次使用：正在从官网加载主板目录…")
            self._start_catalog()

    # ------------------------------------------------------------- 设置（目录更新 / 显示范围）
    def _refresh_days_label(self, days):
        for d, lbl in REFRESH_OPTS:
            if d == days:
                return lbl
        return "7 天"

    def _open_settings(self):
        cfg = self.cfg
        # 平台候选（以当前目录为准；目录未就绪时用标准三平台）
        plat_names = []
        if self.catalog:
            plat_names = [b["name"] for b in self.catalog.get("brands") or []]
        if not plat_names:
            plat_names = ["Intel", "AMD", "其他"]
        # 芯片组候选：(展示文本, 芯片组名)；含所属平台与数量
        chip_opts = []
        if self.catalog:
            for b in self.catalog.get("brands") or []:
                for cs in b.get("chipsets") or []:
                    if cs.get("boards"):
                        chip_opts.append(("%s · %s（%d 款）" % (b["name"], cs["name"],
                                                                len(cs["boards"])), cs["name"]))
        cur_plat = cfg.get("show_platforms") or []
        cur_chip = cfg.get("chip_filter") or []
        cur_days = int(cfg.get("refresh_days") or 0)

        win = tk.Toplevel(self.root)
        win.title("设置")
        _sw, _sh = _fit_size(780, 700, 60)
        # v2.2.0：相对主窗口居中（旧版不定位，Windows 给级联偏移，弹出来不知飘到哪）
        try:
            self.root.update_idletasks()
            _px = self.root.winfo_rootx() + (self.root.winfo_width() - _sw) // 2
            _py = self.root.winfo_rooty() + (self.root.winfo_height() - _sh) // 2
            _aw, _ah = _work_area()
            win.geometry("%dx%d+%d+%d" % (_sw, _sh,
                                          max(0, min(_px, _aw - _sw)),
                                          max(0, min(_py, _ah - _sh))))
        except Exception:
            win.geometry("%dx%d" % (_sw, _sh))
        win.minsize(min(S(740), _sw), min(S(660), _sh))
        win.transient(self.root)
        win.grab_set()
        win.configure(bg=C_BG)
        tk.Frame(win, bg=C_ACCENT, height=S(4)).pack(fill="x", side="top")
        frm = ttk.Frame(win, style="Card.TFrame", padding=S(16))
        frm.pack(fill="both", expand=True)
        # v2.2.1 修复：按钮栏在**内容之前** pack（side="bottom"）—— pack 是按调用
        # 顺序分配空间的，先到先得。旧版按钮栏最后 pack，窗口一旦被压到 minsize
        # （740×660）而内容需要 678px，「保存 / 取消」会被挤出可视区，用户点不到
        # 保存，观感就是「设置里改了配置保存不了」。
        bar = ttk.Frame(frm, style="Card.TFrame")
        bar.pack(side="bottom", fill="x", pady=(S(10), S(0)))

        ttk.Label(frm, text="设置 — 目录更新与显示范围", style="H.TLabel").pack(anchor="w")
        ttk.Label(frm, text="保存后立即生效，无需重启。设置保存于程序目录 msi_bios_checker.cfg。",
                  style="Sub.TLabel").pack(anchor="w", pady=(S(2), S(6)))

        def _sec(parent, title):
            box = tk.Frame(parent, bg=C_INSET,
                           highlightbackground=C_BORDER, highlightthickness=S(1))
            box.pack(fill="x", pady=(S(6), S(0)))
            head = tk.Frame(box, bg=C_INSET)
            head.pack(fill="x")
            tk.Label(head, text=title, font=FONT_B, bg=C_INSET, fg=C_ACCENT_DEEP,
                     anchor="w").pack(side="left", padx=S(12), pady=(S(8), S(0)))
            inner = tk.Frame(box, bg=C_INSET)
            inner.pack(fill="x", padx=S(12), pady=(S(4), S(10)))
            return inner

        # ---------- ① 目录自动刷新间隔（检测频率）
        inner1 = _sec(frm, "① 更新检测 — 目录自动刷新")
        tk.Label(inner1, text="目录自动刷新间隔：", font=FONT, bg=C_INSET,
                 fg=C_TEXT).grid(row=0, column=0, sticky="w")
        v_refresh = tk.StringVar(value=self._refresh_days_label(cur_days))
        ttk.Combobox(inner1, textvariable=v_refresh, state="readonly", width=12,
                     values=[lbl for _d, lbl in REFRESH_OPTS], font=FONT
                     ).grid(row=0, column=1, sticky="w", padx=(S(8), S(0)), ipady=S(2))
        tk.Button(inner1, text="立即更新目录", font=FONT_ACCENT, bg=C_ACCENT_BTN, fg="#ffffff",
                  activebackground=C_ACCENT_BTN_HOT, activeforeground="#ffffff",
                  relief="flat", bd=0, padx=S(12), pady=S(3), cursor="hand2",
                  command=lambda: self._refresh_now(win)
                  ).grid(row=0, column=2, sticky="w", padx=(S(16), S(0)))
        tk.Label(inner1, text="达到间隔后，启动程序时会在后台自动从官网刷新主板目录（新版芯片组 / 新型号自动出现）；\n"
                              "选「不自动刷新」则只在点「立即更新目录」时联网更新。离线时更新失败不影响浏览已有型号。",
                 font=FONT_SS, bg=C_INSET, fg=C_SUB, justify="left"
                 ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(S(4), S(0)))

        # ---------- ② 目录显示范围：平台
        inner2 = _sec(frm, "② 目录显示范围 — 平台")
        plat_vars = {}
        for i, pn in enumerate(plat_names):
            var = tk.BooleanVar(value=(not cur_plat) or (pn in cur_plat))
            plat_vars[pn] = var
            tk.Checkbutton(inner2, text=pn + " 主板", variable=var, font=FONT,
                           bg=C_INSET, fg=C_TEXT, activebackground=C_INSET,
                           activeforeground=C_TEXT, selectcolor=C_CARD,
                           highlightthickness=0, bd=0
                           ).grid(row=0, column=i, sticky="w", padx=(S(0), S(26)))

        # ---------- ③ 目录显示范围：芯片组
        inner3 = _sec(frm, "③ 目录显示范围 — 芯片组")
        v_mode = tk.IntVar(value=0 if not cur_chip else 1)
        tk.Radiobutton(inner3, text="显示全部芯片组", variable=v_mode, value=0,
                       font=FONT, bg=C_INSET, fg=C_TEXT, activebackground=C_INSET,
                       activeforeground=C_TEXT, selectcolor=C_CARD,
                       highlightthickness=0, bd=0).grid(row=0, column=0, sticky="w")
        tk.Radiobutton(inner3, text="仅显示以下勾选的芯片组：", variable=v_mode, value=1,
                       font=FONT, bg=C_INSET, fg=C_TEXT, activebackground=C_INSET,
                       activeforeground=C_TEXT, selectcolor=C_CARD,
                       highlightthickness=0, bd=0).grid(row=0, column=1, sticky="w", padx=(S(20), S(0)))
        if chip_opts:
            box3 = tk.Frame(inner3, bg=C_INSET)
            box3.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(S(6), S(0)))
            lb = tk.Listbox(box3, selectmode="multiple", exportselection=False,
                            font=FONT_S, width=58, height=min(9, max(4, len(chip_opts))),
                            bg=C_CARD, fg=C_TEXT, relief="flat", borderwidth=0,
                            highlightthickness=S(1), highlightbackground=C_BORDER,
                            selectbackground=C_SEL_BG, selectforeground=C_TEXT,
                            activestyle="none")
            lb.pack(side="left", fill="both", expand=True)
            sb3 = ttk.Scrollbar(box3, orient="vertical", command=lb.yview)
            sb3.pack(side="right", fill="y")
            lb.configure(yscrollcommand=sb3.set)
            for _disp, _name in chip_opts:
                lb.insert("end", _disp)
            for i, (_disp, _name) in enumerate(chip_opts):
                if _name in cur_chip:
                    lb.selection_set(i)
            btn_col = tk.Frame(box3, bg=C_INSET)
            btn_col.pack(side="right", fill="y", padx=(S(8), S(0)))

            def _sel_all():
                lb.selection_set(0, "end")

            def _sel_none():
                lb.selection_clear(0, "end")

            def _sel_toggle():
                cur = set(lb.curselection())
                lb.selection_clear(0, "end")
                for i in range(lb.size()):
                    if i not in cur:
                        lb.selection_set(i)
            for text, fn in (("全选", _sel_all), ("全不选", _sel_none), ("反选", _sel_toggle)):
                ttk.Button(btn_col, text=text, width=7,
                           command=fn).pack(pady=(S(0), S(6)), anchor="e")
        else:
            tk.Label(inner3, text="（目录尚未加载，加载后可在此勾选芯片组范围）",
                     font=FONT_S, bg=C_INSET, fg=C_SUB
                     ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(S(6), S(0)))

        # ---------- 按钮（按钮栏已在开头建好并 pack 到 frm 底部）
        ttk.Button(bar, text="恢复默认", command=lambda: self._settings_defaults(
            v_refresh, plat_vars, v_mode, lb if chip_opts else None)).pack(side="left")
        ttk.Button(bar, text="取消", command=win.destroy).pack(side="right")
        ttk.Button(bar, text="保存", style="Accent.TButton",
                   command=lambda: self._settings_apply(
                       win, v_refresh, plat_vars, plat_names, v_mode,
                       lb if chip_opts else None, chip_opts)).pack(side="right", padx=(S(0), S(8)))
        # v2.2.1：按内容实测需求定尺寸与最小尺寸 —— 保证按钮栏与全部区块都放得下，
        # 用户不可能把窗口缩到看不见「保存」的程度。
        try:
            win.update_idletasks()
            _need_w = max(760, frm.winfo_reqwidth() + S(8))
            _need_h = max(700, frm.winfo_reqheight() + S(16))
        except Exception:
            _need_w, _need_h = 780, 700
        _cw, _ch = _fit_size(_need_w, _need_h, 60)
        win.geometry("%dx%d" % (_cw, _ch))
        win.minsize(_cw, _ch)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self.root.wait_window(win)

    def _settings_defaults(self, v_refresh, plat_vars, v_mode, lb):
        """恢复默认：仅把控件复位，需再点「保存」生效。"""
        v_refresh.set(self._refresh_days_label(DEFAULT_REFRESH_DAYS))
        for var in plat_vars.values():
            var.set(True)
        v_mode.set(0)
        if lb is not None:
            lb.selection_clear(0, "end")

    def _settings_apply(self, win, v_refresh, plat_vars, plat_names, v_mode, lb, chip_opts):
        """设置面板「保存」入口（v2.2.1 加固）。

        noconsole 打包（console=False）下，Tk 回调里抛出的异常只会写到 stderr ——
        没有控制台，用户和开发者都看不到，现象就是「点保存什么都没发生 / 配置存不住」。
        这里整段兜住：异常写日志 + 弹窗，写入失败也明确告知配置文件路径，绝不静默。
        """
        try:
            self._settings_commit(win, v_refresh, plat_vars, plat_names,
                                  v_mode, lb, chip_opts)
        except Exception as e:
            _log("settings apply err: %r" % (e,))
            try:
                messagebox.showerror(
                    APP_TITLE,
                    "保存设置时出错，配置未写入：\n%r\n\n详见程序目录下的日志文件。" % (e,),
                    parent=win)
            except Exception:
                pass

    def _settings_commit(self, win, v_refresh, plat_vars, plat_names, v_mode, lb, chip_opts):
        days = DEFAULT_REFRESH_DAYS
        for d, lbl in REFRESH_OPTS:
            if lbl == v_refresh.get():
                days = d
                break
        plats = [pn for pn, var in plat_vars.items() if var.get()]
        if not plats:
            messagebox.showwarning(APP_TITLE, "至少勾选一个平台，否则目录将没有可显示内容。",
                                   parent=win)
            return
        if chip_opts is None:
            # v2.2.1 修复：目录尚未加载时，芯片组区在界面上是灰的（只有一行
            # 「目录尚未加载，加载后可在此勾选」），用户根本看不到也点不到。
            # 旧版此时走 else 分支把 chip_filter 写成 None —— 等于「打开设置点一下
            # 保存，原有芯片组范围被静默清空」。改为原样保留。
            chip_sel = self.cfg.get("chip_filter")
        elif v_mode.get() == 1:
            idxs = lb.curselection()
            if not idxs:
                messagebox.showwarning(APP_TITLE, "已选择「仅显示勾选的芯片组」，请至少勾选一项。",
                                       parent=win)
                return
            chip_sel = [chip_opts[i][1] for i in idxs]
        else:
            chip_sel = None
        # 全平台勾选 -> 存 None（等价于默认，语义更干净）
        plat_store = plats if len(plats) < len(plat_names) else None
        old_days = int(self.cfg.get("refresh_days") or 0)
        # v2.2.1 修复（本层主 bug）：旧版这里是 self.cfg = {三项} —— **整体替换**
        # 会连同 v2.2.0 新增的五个状态键一起抹掉：win（窗口尺寸/位置）、last_slug /
        # last_title（上次查看的型号）、last_dir（保存目录）、expanded（目录树展开
        # 状态）。内存和磁盘同时被清，表现为「进设置点了保存，之前的状态全没了 /
        # 配置保存不住」。改为只覆盖这三项，其余键原样保留。
        self.cfg["refresh_days"] = days
        self.cfg["show_platforms"] = plat_store
        self.cfg["chip_filter"] = chip_sel
        # v2.2.1：检查写盘结果。旧版不检查返回值 —— 写入被安全软件拦截 / 目录只读时
        # 界面照样提示「设置已保存并应用」，用户重启后配置全没，无从判断原因。
        if not save_cfg(self.cfg):
            _log("settings save FAILED -> %s" % _cfg_path())
            messagebox.showwarning(
                APP_TITLE,
                "设置未能写入磁盘，本次修改重启后会丢失：\n%s\n\n"
                "常见原因：程序目录只读、被杀毒 / 安全软件拦截写入。\n"
                "把程序换个可写目录（如桌面）再试。" % _cfg_path(),
                parent=win)
            return
        _log("settings saved -> %s" % _cfg_path())
        win.destroy()
        self._populate_tree()
        # 间隔收严且当前缓存已超期 -> 立即后台刷新（离线失败无碍浏览）
        _c, age = load_catalog_cached()
        if days > 0 and old_days != days and age >= days * 86400:
            self._set_status("刷新间隔已设为 %d 天：当前缓存已超期，正在后台刷新目录…" % days)
            self._start_catalog()
        else:
            self._set_status("设置已保存并应用（目录自动刷新：%s）" % v_refresh.get())

    def _refresh_now(self, win=None):
        """设置面板「立即更新目录」：关弹窗并在后台从官网重拉目录（新版芯片组/型号自动出现）。"""
        try:
            if win is not None and win.winfo_exists():
                win.destroy()
        except Exception:
            pass
        self._set_status("正在从官网刷新主板目录…")
        self._start_catalog()

    def _start_catalog(self):
        """统一的目录抓取入口（v2.2.0）：在途去重 + 统一 busy 标记。

        旧版 4 处各自裸起线程（启动过期 / 首次使用 / 设置保存后超期 / 手动刷新），
        连点两次「↻」会并发两条全量抓取：两条请求抢同一把网络锁串行跑（白等），
        而且后完成者会用**较早的快照**覆盖新结果写盘（save_catalog 后写者胜）。
        另外旧版抓取期间从不发 busy=True，主按钮在目录刷新时是可点的。

        返回 True 表示已启动，False 表示已有抓取在途（调用方可据此提示）。
        """
        if self._cat_busy:
            self._set_status("目录正在刷新中，请稍候…", "run")
            return False
        self._cat_busy = True
        self.q.put(("busy", True))
        threading.Thread(target=self._catalog_worker, daemon=True).start()
        return True

    def _catalog_worker(self):
        def prog(msg):
            self.q.put(("cat_prog", msg))
        try:
            api = self.api
            cat = fetch_catalog(api, progress=prog)
            save_catalog(cat)
            self.q.put(("catalog", cat, None))
        except Exception as e:
            self.q.put(("catalog", None, str(e)[:300]))
        finally:
            self.q.put(("busy", False))

    def _cat_progress(self, msg):
        self._ui_status("目录加载中… %s" % msg)

    def _apply_catalog(self, cat, err):
        self._cat_busy = False          # 抓取结束（成功或失败），放行下一次
        if cat is None:
            self.v_cat.set("目录加载失败")
            self._set_status("目录更新失败：%s\n仍可使用本地缓存的型号。" % (err or ""))
            return
        self.catalog = cat
        self.cat_updated = cat.get("updated", "")
        self._populate_tree()
        self._set_status("目录就绪：%d 款主板（%s 更新）" % (cat.get("total", 0), self.cat_updated))

    # ------------------------------------------------- UI 自适应（v2.2.0）
    def _tv_col_need(self):
        """实测 BIOS 表**每列所需**宽度（表头与所有单元格取较大者 + 单元格内边距）。

        表头样式是 FONT_B（粗体）而测量字体 _fm_tree 是 FONT_S，粗体略宽 —— 加 6%
        补偿，避免"按测量值分配好了、渲染出来表头还是被裁"。
        """
        pad = S(24)                       # 单元格左右内边距合计（实测）
        need = {}
        for cid in ("ver", "date", "size", "note"):
            w = int(self._text_px(str(self.tv.heading(cid, "text"))) * 1.06)
            for iid in self.tv.get_children():
                w = max(w, self._text_px(str(self.tv.set(iid, cid))))
            need[cid] = w + pad
        return need

    def _list_fill(self, on):
        """列表区是否吃满卡片高度（v2.5.5）。

        有数据时 false：列表按行数定高，余量交给卡片底部空行（row 7）。
        空状态时 true：占位块本身没有内容高度，必须由列表行吸收，否则
        「尚未选择主板型号」会挤在卡片顶部一条。
        """
        try:
            self._rf.rowconfigure(2, weight=1 if on else 0)
            self._rf.rowconfigure(7, weight=0 if on else 1)
        except Exception as e:
            _log("list fill err: %r" % (e,))

    def _fit_mfoot(self, _ev=None):
        """栏 2 footer：装不下时按「信息重要性」分级让路（v2.5.5）。

        这一行是 `[共 N 款]  …（弹性）…  [目录: 2026-10-07 11:46]`。
        旧版把右侧标签 pack 到右边就完事了：1180 最小窗下中栏只剩 353px，
        右侧拿到比请求宽更窄的槽，被**硬切**成「目录：2026-10-」——
        日期只显示到月份，读起来像目录时间戳解析失败。

        让路阶梯（先牺牲最后一个）：
          ① `目录: 2026-10-07 11:46`  完整 —— 宽裕时
          ② `目录 2026-10-07`         丢掉时分 —— 中栏典型宽度
          ③ `2026-10-07`              丢掉「目录」二字 —— 很窄
          ④ 整块收掉                  再窄就连日期也不占位
        计数（共 N 款 / 本节 N 款）永不参与让路：它回答「这里有多少东西」，
        是这一栏的主读数；日期只是「数据有多新」。
        """
        try:
            w = self._mfoot.winfo_width()
            if w < S(60):
                return
            full = (self.cat_updated or "").strip()
            if not full:
                return
            lw = self._lbl_cat.winfo_reqwidth()
            gap = S(14)

            def pw(s):
                if not self._fm_mono or not s:
                    return 0
                return int(self.root.tk.call("font", "measure", self._fm_mono, s))

            day = full.split(" ")[0]
            text = ""
            for cand in ("目录: %s" % full, "目录 %s" % day, day):
                if lw + gap + pw(cand) <= w:
                    text = cand
                    break
            if text:
                if not self._lbl_cat_upd.winfo_manager():
                    self._lbl_cat_upd.pack(side="right")
                if self.v_cat_upd.get() != text:
                    self.v_cat_upd.set(text)
            elif self._lbl_cat_upd.winfo_manager():
                # 降到第 ④ 级：不只是不显示，变量也一并清掉 ——
                # 否则「变量里是完整串、屏幕上什么都没有」，调试和门禁读到的
                # 都不是用户看到的东西（这个不一致本身就是个坑）。
                # 宽回来时不丢信息：完整串的真源是 self.cat_updated。
                self._lbl_cat_upd.pack_forget()
                if self.v_cat_upd.get():
                    self.v_cat_upd.set("")
        except Exception as e:
            _log("fit mfoot err: %r" % (e,))

    def _fit_tv_height(self, _ev=None):
        """BIOS 表高度按「数据行数」定，不再吃满卡片（v2.5.5）。

        旧版列表行 weight=1：3 个版本时表格 368px，其中 278px 是空行（实测 75%），
        而详情区被压到 126px 保底。空白在表格**内部**，读起来像「还没加载完」。

        现在行数 = min(max(数据行数, TV_MIN_ROWS), TV_MAX_ROWS, 实际放得下的行数)，
        详情紧跟其下，余量落到卡片底部。放得下的行数由本卡片**实际高度**反推 ——
        不能用请求高度，否则窗外框一缩小就会把详情顶出可视区。

        为什么不会形成布局反馈环：改的是 `tv` 的请求高，而 `rf` 的实际高由父容器
        （body 行 0，weight=1，sticky=nsew）决定，不随子控件请求高变化。
        """
        try:
            rf = self._rf
            h = rf.winfo_height()
            if h < S(240):            # 初次布局的中间态（1px），忽略
                return
            n_rows = len(self.tv.get_children())
            trow_h = max(S(28), self._title_row.winfo_height())
            det_h = max(S(RIGHT_DETAIL_MIN), self._detail_zone.winfo_reqheight())
            # 表头实高 = Treeview 请求高 − 行数 × 行高（用上一次设定的行数反推）。
            # 不能写死：表头高由字体 + 样式 padding 决定，不随 S() 线性缩放。
            head_h = S(TV_HEAD_H)
            if self._tv_h:
                head_h = max(head_h,
                             self.tv.winfo_reqheight() - self._tv_h * S(TV_ROWH))
            # 可用高 = 卡片高 − 卡片内边距 − 标题行 − 列表区上下留白(10/4)
            #          − 详情区 − 详情前留白(8) − 表头
            avail = h - S(32) - trow_h - S(14) - det_h - S(8) - head_h
            fit = int(avail // S(TV_ROWH))
            rows = min(max(n_rows, TV_MIN_ROWS), TV_MAX_ROWS)
            rows = max(1, min(rows, fit))
            if rows != self._tv_h:
                self._tv_h = rows
                self.tv.configure(height=rows)
        except Exception as e:
            _log("fit tv height err: %r" % (e,))

    def _refit_tv_soon(self):
        """空闲时重算表高（详情区请求高变化后调用）。

        为什么用 after_idle 而不是直接调：`_show_detail` 由 `<<TreeviewSelect>>`
        触发，此时详情区的新内容刚 configure、换行高还没结算，直接测 reqheight
        拿到的是**旧值**。after_idle 让几何结算先跑完；合并标志避免一次业务操作
        里多次 set 造成连续重排。
        """
        if self._refit_tv_pending:
            return
        self._refit_tv_pending = True

        def _go():
            self._refit_tv_pending = False
            self._fit_tv_height()

        try:
            self.root.after_idle(_go)
        except Exception:
            self._refit_tv_pending = False

    def _fit_tv_cols(self, _ev=None):
        """BIOS 表列宽：按**实测内容需求**分配（v2.5.0 重写）。

        旧版用固定比例 0.22 / 0.15 / 0.10 / 0.53。实测该比例与实际内容分布不匹配：
          版本列 分到 153 而只需 118（白占 35px）
          发布日期 分到 104 而需 110 ｜ 大小 84 需 86 ｜ 更新说明 356 需 416（被截 60px）
        也就是「列表最该读的那一列（更新说明）被挤掉，最不需要宽的那一列（版本号）
        最富余」。改为：窄列（ver/date/size）取实测需求值，说明列拿走**剩余全部**。
        没有数据行时（首次加载 / 空状态）仍退回比例分配。
        """
        try:
            w = self._list_holder.winfo_width()
            if w < S(200):
                return
            avail = w - S(4)
            fixed = ("ver", "date", "size")
            if self.tv.get_children():
                need = self._tv_col_need()
                cols = {}
                used = 0
                for cid in fixed:
                    cols[cid] = max(S(TV_COL_MIN[cid]), need[cid])
                    used += cols[cid]
                cols["note"] = max(S(TV_NOTE_MIN), avail - used)
                # 总和超出容器时，从「最宽、余量最大」的窄列回收（不跌破各自下限），
                # 回收顺序天然把损失落在版本 / 日期上，先保住说明列。
                over = sum(cols.values()) - avail
                if over > 0:
                    for cid in sorted(fixed, key=lambda c: -cols[c]):
                        if over <= 0:
                            break
                        give = min(over, cols[cid] - S(TV_COL_MIN[cid]))
                        if give > 0:
                            cols[cid] -= give
                            over -= give
                    if over > 0:
                        cols["note"] = max(S(TV_NOTE_MIN), cols["note"] - over)
            else:
                spec = (("ver", 0.22, 150), ("date", 0.15, 104),
                        ("size", 0.10, 84), ("note", 0.53, 200))
                cols = {cid: max(S(minw), int(avail * frac))
                        for cid, frac, minw in spec}
                over = sum(cols.values()) - avail
                if over > 0:
                    for cid in sorted(cols, key=lambda c: -cols[c]):
                        if over <= 0:
                            break
                        minw = dict((c, m) for c, _f, m in spec)[cid]
                        give = min(over, cols[cid] - S(minw))
                        if give > 0:
                            cols[cid] -= give
                            over -= give
            for cid in ("ver", "date", "size", "note"):
                if str(self.tv.column(cid, "width")) != str(cols[cid]):
                    self.tv.column(cid, width=cols[cid])
        except Exception as e:
            _log("tv col fit err: %r" % (e,))

    def _sub_slot_width(self):
        """slug 副标题槽的宽度（含其前方间距）。无内容返回 0。

        用 winfo_reqwidth 而不是 winfo_width：槽被 pack_forget 后 width 归零，
        但 reqwidth 仍是"它需要多宽"，正是让路决策要的量。
        """
        if not self.v_board_sub.get():
            return 0
        try:
            return self.lbl_sub.winfo_reqwidth() + S(10)
        except Exception:
            return 0

    def _set_sub_visible(self, on):
        """显示/隐藏 slug 副标题槽（数据源徽章不受影响）。"""
        if on == (not self._sub_hidden):
            return
        try:
            if on:
                # 用 after= 精确插回**标题之后**。不能写 before=self._right_box：
                # 右侧组是最先 pack 的，插在它之前等于插到标题前面 —— 宽屏下会看到
                # slug 跑到型号标题的左边去（视觉上像"标题被降级成了副标题"）。
                self._sub_box.pack(side="left", padx=(S(10), S(0)),
                                   pady=(S(9), S(0)), after=self.lbl_board_title)
                self._sub_hidden = False
            else:
                self._sub_box.pack_forget()
                self._sub_hidden = True
        except Exception as e:
            _log("sub slot visible err: %r" % (e,))

    def _host_slot_width(self):
        """数据源徽章的槽宽（含前方间距）；文本为空时视为 0。"""
        try:
            if not (self.lbl_host.cget("text") or "").strip():
                return 0
            return self.lbl_host.winfo_reqwidth() + S(10)
        except Exception:
            return 0

    def _set_host_visible(self, on):
        """显示/隐藏数据源徽章（v2.5.5：标题装不下时它是第二个让路的）。"""
        if on == (not self._host_hidden):
            return
        try:
            if on:
                self.lbl_host.pack(side="right", padx=(S(0), S(10)),
                                   after=self.btn_openpage)
                self._host_hidden = False
            else:
                self.lbl_host.pack_forget()
                self._host_hidden = True
        except Exception as e:
            _log("host slot visible err: %r" % (e,))

    def _show_board_title(self, text):
        """设置型号标题：宽度不够时按优先级让路（v2.3.1，v2.5.5 改为三级）。

        让路顺序（先牺牲谁）：
          ① slug 副标题 —— 与标题高度重复（MPG-Z790-EDGE-TI-WIFI ↔ MPG Z790 EDGE TI WIFI）
          ② 数据源徽章 —— 只回答"读的是哪个站"，是能重建的辅助信息
          ③ 标题省略号 —— 主信息，最后才动

        v2.5.5 前的顺序是 ①→③，徽章"永不参与让路"。实测 1180 宽窗口下后果正好相反：
        标题被砍成「MPG Z790 EDGE TI WI…」，而 138px 的徽章**一个像素都没让**。
        主信息给辅助信息让路，是优先级写反了 —— 现在徽章也进让路队列。
        """
        self._title_full = text or ""
        try:
            roww = self._title_row.winfo_width()
            need = 0
            if self._fm_title:
                need = int(self.root.tk.call("font", "measure", self._fm_title,
                                             self._title_full)) + S(TITLE_MEASURE_SLACK)
            btn_w = self.btn_openpage.winfo_reqwidth() + S(8)
            host_w = self._host_slot_width()
            subw = self._sub_slot_width()
            # 副标题只在"扣掉它之后标题仍然放得下"时才留
            want_sub = bool(need) and (roww - btn_w - host_w - subw) >= need
            self._set_sub_visible(want_sub)
            avail = roww - btn_w - host_w - (subw if want_sub else 0)
            # ② 徽章让路：只有"标题确实装不下"时才收，装得下就一直留着
            want_host = True
            if need and avail < need and host_w:
                want_host = False
                avail = roww - btn_w - (subw if want_sub else 0)
            self._set_host_visible(want_host)
            if need and avail >= need:
                self.v_board_title.set(self._title_full)
                return
            if avail >= S(80) and self._fm_title:
                self.v_board_title.set(
                    _ellipsize(self._title_full, avail, self._fm_title, self.root))
                return
        except Exception as e:
            _log("fit board title err: %r" % (e,))
        self.v_board_title.set(self._title_full)

    def _fit_board_title(self, _ev=None):
        """行宽变化时重算标题省略与副标题让路。"""
        self._show_board_title(self._title_full)

    def _refit_title_soon(self):
        """副标题内容变化 → 空闲时重算让路（合并同一轮的多次 set）。

        不能直接同步调用：`v_board_sub` 常在一次业务操作里被 set 多次，
        每次同步重排会让标题闪动。after_idle 只保留最后一次。
        """
        if self._title_refit_job is not None:
            return
        # 先占位再注册：不能写成 `self._x = self.root.after_idle(self._x_now)` ——
        # 回调若在赋值前就跑完（把 _x 清成 None），赋值会再把已完成的 job id 写回去，
        # 于是这个 id 永远留着，后续所有重算请求都被当成"已有排队"而丢弃。
        self._title_refit_job = "pending"
        try:
            job = self.root.after_idle(self._refit_title_now)
            if self._title_refit_job == "pending":
                self._title_refit_job = job
        except Exception as e:
            self._title_refit_job = None
            _log("schedule title refit err: %r" % (e,))

    def _refit_title_now(self):
        self._title_refit_job = None
        self._fit_board_title()

    def _set_dir_display(self, path):
        """设置保存目录的显示（v2.3.1）。

        必须记下**完整路径**再交给显示层省略 —— 不能拿 v_dir 的当前值当原文，
        否则第二次省略就是对"已经省略过的字符串"再省略，路径会一路缩没。
        """
        self._dir_full = path or ""
        self._fit_dir_text()

    def _fit_dir_text(self, _ev=None):
        """按可用宽度省略保存路径（v2.3.1：目录与 4 个按钮同一行）。

        为什么必须显式省略：tk.Label 不做省略，文本超长时它会**撑大所在的
        grid 列**，把右侧按钮压变形（按钮是 sticky="nsew"，会被拉窄）。

        只统计**当前已被布局管理**的按钮：取消下载按钮平时是 grid_remove 的，
        把它的请求宽算进去会让可用宽凭空少 100 多像素，白白压掉一截路径。
        """
        full = self._dir_full
        if not full:
            try:
                self.v_dir.set("")
            except Exception:
                pass
            return
        txt = full
        try:
            roww = self._orow.winfo_width()
            if roww >= S(100):
                btns = [b for b in (self.btn_pick, self.btn_open_dir,
                                    self.btn_cancel, self.btn_dl)
                        if b.winfo_manager()]
                btnw = sum(b.winfo_reqwidth() for b in btns)
                avail = (roww - btnw - self._dir_cap.winfo_reqwidth()
                         - S(8) * 3 - S(12))
                if avail >= S(60) and self._fm_tree:
                    txt = _ellipsize(full, avail, self._fm_tree, self.root)
        except Exception as e:
            _log("fit dir text err: %r" % (e,))
            txt = full
        if self.v_dir.get() != txt:
            try:
                self.v_dir.set(txt)
            except Exception:
                pass

    def _pb_char_px(self):
        """ttk.Label 字符格的基准宽 = measure("0")（字体不可用时按 9px 兜底）。"""
        if self._fm_tree:
            try:
                one = int(self.root.tk.call("font", "measure", self._fm_tree, "0"))
                if one > 0:
                    return one
            except Exception as e:
                _log("measure pb char err: %r" % (e,))
        return S(9)

    def _pb_sample_px(self, compact):
        """进度文案**上界样例**的像素宽（v2.2.2）。

        标签样式 Sub.TLabel 用的就是 FONT_S，而 `_fm_tree` 也是按 FONT_S 建的具名
        字体 —— 量出来的即渲染宽度。不再用「N 字符格」这种估法。
        """
        sample = PB_TXT_SHORT if compact else PB_TXT_FULL
        v = 0
        if self._fm_tree:
            try:
                v = int(self.root.tk.call("font", "measure", self._fm_tree, sample))
            except Exception as e:
                _log("measure pb sample err: %r" % (e,))
                v = 0
        if v <= 0:      # 字体不可用时的兜底估算（与 _text_px 同一套口径）
            v = sum(S(9) if ord(ch) < 128 else S(15) for ch in sample)
        return v

    def _pb_label_chars(self, compact):
        """标签格宽度（字符）＝ 上界样例像素宽向上取整 + 安全余量。"""
        one = self._pb_char_px()
        px = self._pb_sample_px(compact) + S(2)
        return max(PB_LBL_SHORT, -(-px // one) + PB_LBL_PAD)

    def _pb_label_px(self, compact):
        """标签格的实际像素宽 —— 降级阈值与标签宽度共用这一个口径（v2.2.2）。"""
        return self._pb_label_chars(compact) * self._pb_char_px()

    def _fit_progress_text(self, _ev=None):
        """窄窗口下把进度文案压短。

        判据：「进度行宽 - 标签格宽 - 内边距」还剩多少给进度条 —— 不足 PB_BAR_MIN
        就切短文案。标签格宽与阈值共用同一个实测口径（见 _pb_label_px）。

        v2.2.2 修正了 v2.2.0 的错误结论（旧注释称「1200×780 默认尺寸进度行 756px 不
        触发」）—— 那个 756px 只在**目录还没到达、左栏还是 360px** 时成立。目录一到
        达左栏扩到 417px，进度行掉到 699px，旧阈值 728px 于是被击穿。修正前后实测
        （100% DPI，目录已加载）：

            1100×780  进度行 599px   修正前 压短   修正后 压短   ← 窄窗口行为不变
            1200×780  进度行 699px   修正前 **压短**  修正后 完整   ← 本次修复点
            1280×780  进度行 779px   修正前 完整   修正后 完整
        """
        try:
            row = self._pbar_row.winfo_width()
            if row < S(100):
                return
            need = (S(12) + self._pb_label_px(False) + S(PB_LBL_SLACK)
                    + S(PB_BAR_MIN))
            compact = row < need
            grid = self._pb_label_chars(compact)
            if int(str(self.lbl_pb.cget("width"))) != grid:
                self.lbl_pb.configure(width=grid)
            if compact != self._pb_compact:
                self._pb_compact = compact
                _log("进度文案%s（进度行 %dpx / 需要 %dpx / 字格 %d）"
                     % ("压短" if compact else "恢复完整", row, need, grid))
        except Exception as e:
            _log("fit progress text err: %r" % (e,))

    # ------------------------------------------------- 设置 / 状态持久化（v2.2.0）
    def _persist(self, **kv):
        """合并写入设置（内存 + 落盘）；值未变化时不落盘。返回是否真的改了。"""
        changed = False
        for k, v in kv.items():
            if self.cfg.get(k) != v:
                self.cfg[k] = v
                changed = True
        if changed:
            save_cfg(self.cfg)
        return changed

    def _restore_geometry(self):
        """返回 (物理宽, 物理高, geometry 串)。优先用上次保存的尺寸与位置。"""
        # v2.5.0：三栏布局需要更宽的默认窗口（宽度账见常量区注释）
        w, h = _fit_size(WIN_W, WIN_H, 40)
        geo = "%dx%d" % (w, h)
        win = self.cfg.get("win")
        try:
            if isinstance(win, (list, tuple)) and len(win) == 4:
                w2, h2 = _fit_size(int(win[0]), int(win[1]), 40)
                x, y = int(win[2]), int(win[3])
                aw, ah = _work_area()
                # 至少 160×80 落在工作区内才认为位置仍可用（换屏/改分辨率后失效）
                if (-w2 + 160) <= x <= (aw - 160) and 0 <= y <= (ah - 80):
                    return w2, h2, "%dx%d+%d+%d" % (w2, h2, x, y)
                w, h = w2, h2
                geo = "%dx%d" % (w, h)
        except Exception as e:
            _log("restore geometry err: %r" % (e,))
        return w, h, geo

    def _on_close(self):
        """关窗前保存状态：窗口尺寸/位置 + 目录树展开状态（下次启动原样恢复）。"""
        try:
            self._remember_expanded()
        except Exception:
            pass
        try:
            self.root.update_idletasks()
            sc = DPI_SCALE if DPI_SCALE > 0 else 1.0
            self._persist(win=[int(round(self.root.winfo_width() / sc)),
                               int(round(self.root.winfo_height() / sc)),
                               int(self.root.winfo_x()), int(self.root.winfo_y())],
                          left_w=int(self._left_user_w or 0))
        except Exception as e:
            _log("save geometry err: %r" % (e,))
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_cat_open(self, _ev=None):
        """目录树展开/收起 → 记录当前展开的芯片组名。"""
        self._remember_expanded()

    def _remember_expanded(self):
        """把目录树中「已展开的芯片组名」写进设置（去掉树节点文案里的「（N 款）」）。"""
        try:
            names = []
            for p_iid in self.cat_tree.get_children(""):
                for c_iid in self.cat_tree.get_children(p_iid):
                    if self.cat_tree.item(c_iid, "open"):
                        txt = str(self.cat_tree.item(c_iid, "text") or "")
                        names.append(re.sub(r"（\d+ 款）$", "", txt).strip())
            if self.cfg.get("expanded") != names:
                self.cfg["expanded"] = names
                save_cfg(self.cfg)
        except Exception as e:
            _log("remember expanded err: %r" % (e,))

    def _restore_last_board(self):
        """启动时恢复上次查看的主板（目录就绪后调用一次）。"""
        slug = (self.cfg.get("last_slug") or "").strip()
        if not slug or self.cur_slug:
            return
        c_iid = self._nav_iid_of_slug(slug)
        if not c_iid:
            _log("上次查看的型号 %s 不在当前目录／过滤范围内，跳过恢复" % slug)
            return
        self.cat_tree.selection_set(c_iid)
        self.cat_tree.see(c_iid)
        self._fill_board_col(c_iid)          # 先填栏 2，再从中选中该型号
        for iid, (s, t) in self.iid_board.items():
            if s == slug:
                self.board_tree.selection_set(iid)
                self.board_tree.see(iid)
                self._load_board(s, t)
                return
        _log("上次查看的型号 %s 在本组里找不到，跳过恢复" % slug)

    # ------------------------------------------------- 目录树列宽自适应（v2.1.1）
    def _text_px(self, text):
        """用与目录树相同的字体实测文本像素宽（带缓存，DPI 变化自动失效）。

        ⚠ 隐含耦合（v2.5.3 补记）：`_fm_tree` 是按 `FONT_S` 建的量宽字体，
        而栏 2 的 `_ellipsize_board()` 也走这里量型号名宽度。两者**当前恰好同族
        同字号**（`Cat.Treeview` 与 `Mod.Treeview` 都配 `font=FONT_S`），所以结果
        正确；但只要有人给 `Mod.Treeview` 单独换字体而 `_fm_tree` 没跟着换，
        栏 2 的省略号就会静默算错（截太短或是溢出）。改栏 2 字体时务必同步这里。
        """
        if self._px_dpi != _DPI:
            self._px_cache.clear()
            self._px_dpi = _DPI
        v = self._px_cache.get(text)
        if v is None:
            v = 0
            if self._fm_tree:
                try:
                    v = int(self.root.tk.call("font", "measure", self._fm_tree, text))
                except Exception:
                    v = 0
            if v <= 0:      # 字体不可用时的兜底估算（100% 下：半角 9px / 全角 15px）
                v = sum(S(9) if ord(ch) < 128 else S(15) for ch in text)
            self._px_cache.put(text, v)
        return v

    def _nav_col_need(self):
        """栏 1（平台 / 芯片组）所需的 **#0 列宽**。基于全量目录，与搜索/过滤无关，
        避免输入搜索词时列宽来回抖动。"""
        cat = self.catalog or {}
        key = (_DPI, cat.get("updated"), cat.get("total"))
        if self._nav_need_key == key:
            return self._nav_need_v
        # 文本可用宽 = 列宽 - 左内边距(CELL_PAD_X) - 右侧留白(CAT_TREE_PAD)。
        # （曾误写为 S(1 + CAT_TREE_PAD)，把左内边距当成 1px —— 实测是 17px。）
        pad = S(CELL_PAD_X + CAT_TREE_PAD)
        need = S(NAV_TREE_MIN)         # 初值是**列宽**下限，不是卡片宽
        for b in cat.get("brands") or []:
            chips = b.get("chipsets") or []
            n_b = sum(len(cs.get("boards") or []) for cs in chips)
            need = max(need, self._text_px("%s 主板（%d 款）" % (b["name"], n_b))
                       + pad + S(CAT_IND_PAD))
            for cs in chips:
                bs = cs.get("boards") or []
                need = max(need, self._text_px(
                    "%s（%d 款）" % (cs["name"], len(bs))) + pad + S(CAT_IND_PAD))
        self._nav_need_key, self._nav_need_v = key, need
        return need

    def _board_col_need(self):
        """栏 2（型号）所需的 **#0 列宽**。

        v2.5.0 的设计取舍：这里**故意不追求装下最长的那一款**。最长型号名实测
        352px，会让栏 2 涨到 417（正是重构前左栏的病根），把宽度从 BIOS 表抢走。
        取 P95 分位（实测 277px）作为目标，超出的少数几款由悬停提示补全
        （见 _on_board_motion），上限再由 BOARD_COL_MAX 夹一次。
        """
        cat = self.catalog or {}
        key = (_DPI, cat.get("updated"), cat.get("total"))
        if self._board_need_key == key:
            return self._board_need_v
        pad = S(CELL_PAD_X + CAT_TREE_PAD)
        ws = []
        for b in cat.get("brands") or []:
            for cs in b.get("chipsets") or []:
                for bd in cs.get("boards") or []:
                    ws.append(self._text_px(bd["title"]) + pad)
        ws.sort()
        if not ws:
            need = S(CAT_TREE_MIN)     # 初值是**列宽**下限，不是卡片宽
        elif len(ws) < 20:
            need = ws[-1]                     # 样本太少时不敢用分位，直接取上界
        else:
            # P95：留 5% 的长名给悬停提示（501 款里约 25 款）
            need = ws[min(len(ws) - 1, int(len(ws) * 0.95))]
        self._board_need_key, self._board_need_v = key, need
        return need

    # ------------------------------------------------- v2.3.1 左右栏分隔
    def _make_split(self, parent, col, which):
        """造一条可拖拽分隔条（v2.5.0：栏1|栏2 与 栏2|栏3 共用同一套逻辑）。

        which 记「这是第几条」，供 _split_press/_motion 反查该拖哪一栏。
        """
        sp = tk.Frame(parent, bg=C_BG, width=S(SPLIT_W), cursor="sb_h_double_arrow")
        sp.grid(row=0, column=col, sticky="ns")
        sp.grid_propagate(False)          # 不让里面的细线把自己撑宽
        line = tk.Frame(sp, bg=C_BORDER, width=S(1))
        line.place(relx=0.5, rely=0.0, anchor="n", relheight=1.0)
        self._bind_hover(line, C_BORDER, C_SUB)      # hover 亮一档（弹簧）
        for _sw in (sp, line):
            _sw.bind("<ButtonPress-1>", self._split_press)
            _sw.bind("<B1-Motion>", self._split_motion)
            _sw.bind("<ButtonRelease-1>", self._split_release)
            _sw.bind("<Double-Button-1>", self._split_reset)
            _sw.bind("<Enter>", lambda _e=None, c=sp:
                     self._cursor_split(True, c), add="+")
            _sw.bind("<Leave>", lambda _e=None, c=sp:
                     self._cursor_split(False, c), add="+")
        sp._which = which
        return sp

    def _cursor_split(self, on, w=None):
        try:
            (w or self._split).configure(
                cursor="sb_h_double_arrow" if on else "arrow")
        except Exception:
            pass

    def _col_limits(self, which, nav_w=0):
        """三栏各自的宽度上下限（单位 = 卡片宽）。

        上限保证栏 3（BIOS 明细）不被挤到 DETAIL_MIN 以下；下限保证那一栏自己还能用。
        窗口极窄时 hi 可能小于 lo —— 此时以下限为准（宁可挤右栏，也不能让导航塌掉：
        导航塌了就没法选型了）。
        """
        avail = (self._body_width() - S(BODY_PAD_X) * 2 - S(SPLIT_W) * 2)
        if which == 1:
            lo = S(NAV_COL_MIN)
            hi = min(S(NAV_COL_MAX), avail - S(BOARD_COL_MIN) - S(DETAIL_MIN))
        else:
            lo = S(BOARD_COL_MIN)
            hi = min(S(BOARD_COL_MAX),
                     avail - max(nav_w, S(NAV_COL_MIN)) - S(DETAIL_MIN))
        return lo, (hi if hi > lo else lo)

    def _left_limits(self):
        """（v2.5.0 起由 _col_limits 取代，保留此名以免外部探针直接报错）"""
        return self._col_limits(1)

    def _set_col_widths(self, nav=None, board=None):
        """设定栏 1 / 栏 2 的卡片宽，并让两棵树各自的 #0 列宽同步跟上。

        列宽必须一起改：卡片宽了列宽不变 → 树右侧留一条空白；卡片窄了列宽不变
        → 型号名被裁。两者是「列宽 + CAT_CARD_OVER = 卡片宽」这一个约束的两头。
        注意 Tk 部分选项返回 Tcl_Obj，数值比较前统一 str()。
        返回实际生效的 (nav, board)。
        """
        if nav is None:
            nav = self._lf.winfo_width()
        lo1, hi1 = self._col_limits(1)
        nav = int(max(lo1, min(hi1, nav)))
        if board is None:
            board = self._mf.winfo_width()
        lo2, hi2 = self._col_limits(2, nav)
        board = int(max(lo2, min(hi2, board)))
        if str(self._lf.cget("width")) != str(nav):
            self._lf.configure(width=nav)
        if str(self._mf.cget("width")) != str(board):
            self._mf.configure(width=board)
        for tree, card_w, tmin in ((self.cat_tree, nav, NAV_TREE_MIN),
                                   (self.board_tree, board, CAT_TREE_MIN)):
            # 列宽 = 卡片宽 − 卡片开销，但不低于**该栏自己的**树列下限。
            # 用错下限的后果很实在：导航栏套 220 会让列宽超出卡片容量 30px。
            col = max(S(tmin), card_w - S(CAT_CARD_OVER))
            if str(tree.column("#0", "width")) != str(col):
                tree.column("#0", width=col)
            if str(tree.column("#0", "minwidth")) != str(col):
                tree.column("#0", minwidth=col)
        return nav, board

    def _set_left_width(self, want, user=False):
        """（v2.5.0 起由 _set_col_widths 取代，保留此名兼容旧探针）"""
        return self._set_col_widths(nav=want)[0]

    def _split_press(self, e):
        which = int(getattr(e.widget, "_which", 0))
        base = self._lf.winfo_width() if which == 0 else self._mf.winfo_width()
        self._split_drag = (e.x_root, base, which)
        return "break"

    def _split_motion(self, e):
        if not self._split_drag:
            return
        x0, w0, which = self._split_drag
        self._split_apply(w0 + (e.x_root - x0), which)
        return "break"

    def _split_apply(self, want, which=0):
        """拖拽中实时设宽。只在**松手后**写盘，避免拖动过程里反复写配置文件。

        拖栏 2 的左边界时，同时把栏 1 一起给上去 —— 否则栏 2 变宽只会从栏 3 拿，
        用户会觉得「拖了没反应」。
        """
        if which == 0:
            self._nav_user_w = self._set_col_widths(nav=want)[0]
        else:
            self._board_user_w = self._set_col_widths(board=want)[1]

    def _split_release(self, _e=None):
        if not self._split_drag:
            return
        self._split_drag = None
        try:
            self._persist(nav_w=int(self._nav_user_w or 0),
                          board_w=int(self._board_user_w or 0))
        except Exception as _ex:
            _log("save nav_w err: %r" % (_ex,))
        return "break"

    def _split_reset(self, e=None):
        """双击分隔条 = 丢弃两条栏的手动宽度，回到自适应（并清零持久化值）。"""
        self._nav_user_w = 0
        self._board_user_w = 0
        self._split_drag = None
        try:
            self._persist(nav_w=0, board_w=0)
        except Exception as _ex:
            _log("reset nav_w err: %r" % (_ex,))
        self._auto_fit_cols()
        return "break"

    def _body_width(self):
        """布局区可用宽度（尚未布局时按目标窗口尺寸估算）。"""
        w = self._body.winfo_width() if self._body else 0
        if w < S(200):
            w = _fit_size(WIN_W, WIN_H, 40)[0] - S(40)
        return w

    def _auto_fit_cols(self):
        """按实测文本宽度设定两条导航栏的宽度（栏 3 吃剩余，无需设宽）。

        列宽 = 实测需求值（因此任何型号名都完整显示，不再被裁）；左栏宽度由列宽
        驱动（grid 传播），右栏自动让位。仅保留一个「右栏保底宽度」软上限：只有
        当窗口窄到右栏将无法正常显示、或将来目录出现超长型号名时才夹紧，避免为
        左侧目录牺牲右侧明细（当前目录实测需 351px，1200 窗口下上限 468px，余量充足）。
        """
        try:
            # v2.3.1：用户拖过分隔条就一直用用户宽度 —— 拖拽是对布局的**显式意图**，
            # 不该被下一次自适应覆盖（否则一改窗口大小就"弹回去"，很恼人）。
            # 出口有两个：双击分隔条重置，或删掉配置里的 nav_w / board_w。
            if self._nav_user_w and self._board_user_w:
                self._set_col_widths(nav=self._nav_user_w,
                                     board=self._board_user_w)
                return
            # v2.2.0：目录尚未加载时**不要**按"空目录"去算列宽 —— 那会得到下限
            # CAT_TREE_MIN(220)，把左栏从设计初始 360px 缩成 280px，目录到达后又跳
            # 回 411px（首次使用 / 网络慢时左边先塌一下再弹开）。
            # 也不能直接 return：_lf 关了 grid 传播，宽度只能由这里显式赋值，
            # 不赋值就停在默认 0（实测 1px，左栏直接消失）。所以此处直接用
            # CAT_TREE_INIT 兜底，保持设计初始观感宽度。
            if self.catalog and self.catalog.get("brands"):
                nav_need = self._nav_col_need()
            else:
                nav_need = S(NAV_COL_MIN)
            # v2.3.1：宽度取三者之最 ——
            #   ① floor = 型号名完整所需（硬底线：回到"裁型号名"是历史倒退，
            #      见 v2.3.7 的教训 —— 写死 300px 装不下 326px 的长型号名）
            #   ② ratio = 窗口比例（宽屏下左栏跟着长，避免右栏宽到一行读不完）
            #   ③ 上限 LEFT_MAX（超过就没有目录/明细的主次感了）
            # 上下限夹紧在 _set_left_width 里统一做（那里还有右栏保底约束）。
            # 栏 1：只装平台 / 芯片组，实测需求 + 卡片开销；夹在 [NAV_COL_MIN, MAX]
            nav = min(S(NAV_COL_MAX), max(S(NAV_COL_INIT),
                                          nav_need + S(CAT_CARD_OVER)))
            # 栏 2：按型号名 P95 的需求；夹在 [BOARD_COL_MIN, MAX]
            if self.catalog and self.catalog.get("brands"):
                b_need = self._board_col_need()
            else:
                b_need = S(CAT_TREE_MIN)
            board = min(S(BOARD_COL_MAX), max(S(BOARD_COL_INIT),
                                              b_need + S(CAT_CARD_OVER)))
            # 用户单独拖过某一条时，只覆盖那一条
            if self._nav_user_w:
                nav = self._nav_user_w
            if self._board_user_w:
                board = self._board_user_w
            self._set_col_widths(nav=nav, board=board)
        except Exception as _e:
            _log("三栏宽度自适应失败: %r" % (_e,))

    # v2.5.0：旧名保留为别名（外部探针与旧调用点仍用 _auto_fit_cat）
    _auto_fit_cat = _auto_fit_cols

    def _cat_ph_set(self, text):
        """栏 1 空列表占位（v2.5.5）：text 为空即隐藏。"""
        try:
            if text:
                self._cat_ph.configure(text=text)
                self._cat_ph.place(relx=0.5, rely=0.32, anchor="center")
            else:
                self._cat_ph.place_forget()
        except Exception as e:
            _log("cat placeholder err: %r" % (e,))

    def _board_ph_set(self, text):
        """栏 2 空列表占位（v2.5.5）：text 为空即隐藏。"""
        try:
            if text:
                self._board_ph.configure(text=text)
                self._board_ph.place(relx=0.5, rely=0.28, anchor="center")
            else:
                self._board_ph.place_forget()
        except Exception as e:
            _log("board placeholder err: %r" % (e,))

    def _populate_tree(self):
        """按当前设置（平台 / 芯片组过滤）+ 搜索词重建左侧主板目录树。

        v2.4.0：新增实时搜索 —— 型号名或芯片组名命中即保留，命中芯片组自动展开，
        目录里找不到时给出「去官网搜索」出口（覆盖已停售型号）。
        """
        show_plat = self.cfg.get("show_platforms") or None
        chip_flt = self.cfg.get("chip_filter") or None
        q = self._search_q
        # v2.2.0：恢复上次手动展开的芯片组（搜索态下全部展开，不套用记录）
        _expand = set() if q else set(self.cfg.get("expanded") or [])
        self.cat_tree.delete(*self.cat_tree.get_children())
        self.board_tree.delete(*self.board_tree.get_children())
        self.iid_chip = {}
        self.iid_board = {}
        self._current_chip = (None, [])
        self._search_hits = 0
        # v2.3.5 防护：目录尚未加载（None / 缺 brands）时清空树并提示，避免 .get 崩溃
        if not self.catalog or not self.catalog.get("brands"):
            self.v_cat.set("目录加载中…")
            self._cat_ph_set("正在读取主板目录…")
            self._board_ph_set("目录就绪后\n这里会列出型号")
            return
        n_vis = 0
        first_iid = None
        for b in self.catalog.get("brands") or []:
            name = b["name"]
            if show_plat and name not in show_plat:
                continue
            chips = [cs for cs in b.get("chipsets") or []
                     if not (chip_flt and cs["name"] not in chip_flt)]
            # 每组先算出「搜索后仍然可见的型号」，组里一条都不剩就不建这一组
            rows = []
            for cs in chips:
                boards = cs.get("boards") or []
                if not boards:
                    continue
                if q:
                    if q not in (cs.get("name") or "").lower():
                        boards = [bd for bd in boards
                                  if q in (bd.get("title") or "").lower()]
                    if not boards:
                        continue
                rows.append((cs, boards))
            n_brand = sum(len(bs) for _cs, bs in rows)
            if n_brand == 0:
                continue
            p_iid = self.cat_tree.insert("", "end", open=True,
                                         text="%s 主板（%d 款）" % (name, n_brand),
                                         tags=("platform",))
            for cs, boards in rows:
                c_iid = self.cat_tree.insert(
                    p_iid, "end", open=False,
                    text="%s（%d 款）" % (cs["name"], len(boards)),
                    tags=("chipset",))
                # 栏 1 只存「这组有哪些型号」，型号本体交给栏 2
                self.iid_chip[c_iid] = (cs, boards)
                if first_iid is None:
                    first_iid = c_iid
            n_vis += n_brand
        if q:
            self._search_hits = n_vis
        total_all = self.catalog.get("total", 0)
        if n_vis == 0:
            self.v_cat.set("0 款")
            self._cat_ph_set("没有匹配的型号" if q else "没有可显示的型号")
            if not q:
                self._set_status("当前设置下没有可显示的型号，请点右上角「设置」调整范围", "warn")
        elif q:
            self.v_cat.set("命中 %d 款" % n_vis)
            self._cat_ph_set("")
        elif n_vis == total_all:
            self.v_cat.set("共 %d 款" % n_vis)
            self._cat_ph_set("")
        else:
            self.v_cat.set("%d / %d 款" % (n_vis, total_all))
            self._cat_ph_set("")
        # 搜索无命中 -> 显示「去官网搜索」出口
        try:
            if q and not n_vis:
                if not self._nores.winfo_manager():
                    self._nores.grid()
            elif self._nores.winfo_manager():
                self._nores.grid_remove()
        except Exception:
            pass
        if self.cat_updated:
            # v2.5.0：栏 1 变窄后「目录更新: 」前缀把时间戳挤出卡片（实测被裁成
            # "…12:4("）。缩短为「目录」，时间戳完整可见。
            # v2.5.5：宽度不够时 _fit_mfoot 会把它继续降级（丢时分 → 丢前缀 → 收掉）
            self.v_cat_upd.set("目录: %s" % self.cat_updated)
            try:
                self.root.after_idle(self._fit_mfoot)
            except Exception:
                pass
        # v2.5.0：选中导航栏里含当前型号的芯片组 → 刷新栏 2（型号）
        pick = self._nav_iid_of_slug(self.cur_slug) or first_iid
        if pick:
            if not self.cat_tree.selection():
                self.cat_tree.selection_set(pick)
                self.cat_tree.see(pick)
            self._fill_board_col(self.cat_tree.selection()[0])
        else:
            self._fill_board_col(None)
        # v2.2.0：启动后恢复上次查看的主板（只做一次；搜索/改设置触发的重建不重复恢复）
        if not self._restored:
            self._restored = True
            self._restore_last_board()
        # v2.5.0：按实测宽度设定两条导航栏
        self._auto_fit_cols()

    def _on_tree_select(self, _ev=None):
        """栏 1 选中芯片组 → 刷新栏 2。"""
        sel = self.cat_tree.selection()
        if not sel:
            return
        self._fill_board_col(sel[0])

    def _toggle_collapse_all(self):
        """一键展开 / 折叠全部平台节点（参照 asus_bios_checker v2.2.0）。

        按「当前是否有任一节点展开」决定本次是收起还是展开 —— 这样按钮语义与
        用户看到的状态永远一致，不需要额外记状态位（少了"状态不同步"这类 bug）。
        """
        try:
            kids = self.cat_tree.get_children("")
            if not kids:
                return
            any_open = any(bool(self.cat_tree.item(k, "open")) for k in kids)
            for k in kids:
                self.cat_tree.item(k, open=not any_open)
            try:
                self.btn_cat_collapse.configure(
                    text="展开全部" if any_open else "折叠全部")
            except Exception:
                pass
        except Exception as _e:
            _log("collapse all err: %r" % (_e,))

    def _nav_iid_of_slug(self, slug):
        """反查「含该型号的芯片组」在栏 1 的 iid（没有则 None）。"""
        if not slug:
            return None
        for c_iid, (_cs, boards) in self.iid_chip.items():
            for bd in boards:
                if bd.get("slug") == slug:
                    return c_iid
        return None

    def _fill_board_col(self, c_iid):
        """栏 2：把选中芯片组下的型号填进型号列表。

        只在「当前查看的型号恰好在这个组里」时自动选中它 —— 否则不选中，
        让栏 3 保持空状态。这样启动时不会莫名其妙自动加载第一款主板。
        """
        self.board_tree.delete(*self.board_tree.get_children())
        self.iid_board = {}
        hit = self.iid_chip.get(c_iid) if c_iid else None
        if not hit:
            self._current_chip = (None, [])
            self.v_board_n.set("—")
            self._board_ph_set("从左侧选择一个芯片组")
            return
        cs, boards = hit
        self._current_chip = (cs.get("name"), boards)
        self._board_ph_set("")
        for bd in boards:
            iid = self.board_tree.insert("", "end", text=bd["title"])
            self.iid_board[iid] = (bd["slug"], bd["title"])
        # v2.5.5：加上「本节」二字 —— 这个数是**当前芯片组**下的型号数，底部 footer
        # 的「共 501 款」是**全库**数量。两个数字并排出现却不说明口径，读者只会困惑
        # 「到底有多少款」。
        self.v_board_n.set("本节 %d 款" % len(boards))
        for iid, (s, _t) in self.iid_board.items():
            if s and s == self.cur_slug:
                self.board_tree.selection_set(iid)
                self.board_tree.see(iid)
                break
        self._fit_board_col_w()

    def _fit_board_col_w(self):
        """栏 2 的 #0 列宽跟随卡片宽（卡片被拖宽时列宽一起跟上）。"""
        try:
            w = self._mf.winfo_width()
            if w < S(80):
                return
            # v2.5.5：下限从 CAT_TREE_MIN(220) 降到 120。
            # 旧写法 col = max(220, w-60)：窗口缩到 1180 时卡片只剩约 193px，
            # 列宽却被撑在 220 —— Tk 会**夹住**列宽并按控件宽度硬切文本，
            # 而 _ellipsize_board 仍按 220 算可用宽，于是"算得下"的名字被切掉尾巴、
            # 连省略号都没有。现在列宽跟着卡片走，省略才有意义。
            col = max(S(120), w - S(CAT_CARD_OVER))
            if str(self.board_tree.column("#0", "width")) != str(col):
                self.board_tree.column("#0", width=col)
            if str(self.board_tree.column("#0", "minwidth")) != str(col):
                self.board_tree.column("#0", minwidth=col)
            self._ellipsize_board()
        except Exception as _e:
            _log("fit board col err: %r" % (_e,))

    def _ellipsize_board(self):
        """v2.5.1：栏 2 里超出列宽的型号名改为「尾部 …」，不再硬切。

        完整名一直保留在 self.iid_board[iid] 里（tooltip 与后续下载都用它），
        这里只改**显示文本** —— 所以不会影响任何功能。

        v2.5.5：可用宽取「列宽」与「控件实测宽」的**较小值**。列宽带 minwidth，
        控件宽度却可以被父容器压得更小；只用列宽算会高估可用宽，结果是文本刚好
        超出可视区、被 Tk 硬切掉尾部而又没走到省略分支（1180 宽窗口下的实测现象）。
        """
        try:
            colw = int(self.board_tree.column("#0", "width"))
            vis = int(self.board_tree.winfo_width())
            if vis > 1:
                colw = min(colw, vis)
            avail = colw - S(CELL_PAD_X + CAT_TREE_PAD)
            if avail < S(40):
                return
            for iid, (_slug, full) in self.iid_board.items():
                disp = (full if self._text_px(full) <= avail
                        else self._ellipsize(full, avail))
                if self.board_tree.item(iid, "text") != disp:
                    self.board_tree.item(iid, text=disp)
        except Exception as _e:
            _log("ellipsize board err: %r" % (_e,))

    def _ellipsize(self, s, avail, ell="\u2026"):
        """把 s 截到 measure 后不超过 avail（尾部补省略号）。

        v2.5.3：改为委托模块级 `_ellipsize`。原来这里另写了一份二分，与模块级那份
        是**同一算法**（v2.5.1 加省略号时没复用），唯一差别是量宽走 `_text_px`
        （带 LRU 缓存）。委托后缓存收益不变，重复实现消失，将来改口径只需改一处。
        实测两版输出在本工程数据上**完全一致**（差异 0 次），属纯去重、无行为变化。
        """
        return _ellipsize(s, avail, None, None, measure=self._text_px, ell=ell)

    def _on_board_select(self, _ev=None):
        """栏 2 选中型号 → 查 BIOS。"""
        sel = self.board_tree.selection()
        if not sel:
            return
        hit = self.iid_board.get(sel[0])
        if hit:
            self._load_board(*hit)

    def _on_board_motion(self, ev):
        """型号名被列宽截断时给悬停提示。

        栏 2 刻意不按「最长的那一款」定宽（见 _board_col_need 的取舍说明），
        被截的少数长名靠这个提示补全 —— 保证信息不丢，又不为离群值付宽度。
        """
        iid = self.board_tree.identify_row(ev.y)
        if iid == self._hover_board:
            return
        self._hover_board = iid or None
        self._hide_tip()
        if not iid:
            return
        # v2.5.1：显示文本可能已加省略号 —— 提示必须用**完整名**（iid_board 里那份）
        _rec = self.iid_board.get(iid)
        title = _rec[1] if _rec else self.board_tree.item(iid, "text")
        colw = int(self.board_tree.column("#0", "width"))
        if self._text_px(title) <= colw - S(CELL_PAD_X + CAT_TREE_PAD):
            return                      # 完整可见，不必提示
        try:
            tw = tk.Toplevel(self.root)
            tw.wm_overrideredirect(True)
            try:
                tw.attributes("-topmost", True)
            except Exception:
                pass
            tk.Label(tw, text=title, font=FONT_S, bg=C_HEADING, fg=C_TEXT,
                     padx=S(8), pady=S(4)).pack()
            tw.wm_geometry("+%d+%d" % (ev.x_root + S(14), ev.y_root + S(20)))
            self._tip = tw
        except Exception as _e:
            _log("board tip err: %r" % (_e,))
            self._tip = None

    def _hide_tip(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

    def _on_board_leave(self, _ev=None):
        self._hover_board = None
        self._hide_tip()

    # ------------------------------------------------------------- BIOS 查询
    def _load_board(self, slug, title):
        if not slug:
            messagebox.showwarning(APP_TITLE, "该型号缺少有效的官网标识（%s）" % title, parent=self.root)
            return
        # v2.2.0 单飞：旧版只用一个 `_loading_slug` 记「最后一个型号」，A→B→A 的
        # 快速切换会为 A 重复发请求；改为按 slug 的在途标记。
        if slug in self._panel_inflight:
            self._enter_loading(slug, title)
            self._set_status("正在查询 %s 的 BIOS 信息…（同型号请求已在途）" % title, "run")
            return
        # v2.2.0 面板缓存：命中则不发网络请求，切型号来回点不再重复打官网
        cached = self._panel_cache.get(slug)
        if cached is not None and (time.time() - cached[0]) < PANEL_TTL:
            self._enter_loading(slug, title)
            self._apply_board((slug, title, cached[1], cached[2], None, cached[3]))
            self._set_status("%s · 共 %d 个 BIOS 版本（内存缓存）"
                             % (title, len(self.cur_items)), "ok")
            return
        self._enter_loading(slug, title)
        self._panel_inflight[slug] = True
        self.q.put(("busy", True))
        threading.Thread(target=self._board_worker, args=(slug, title), daemon=True).start()

    def _enter_loading(self, slug, title):
        """把界面切到「查询中」态（v2.2.0 由 _load_board 抽出，缓存命中/单飞复用）。"""
        self._loading_slug = slug
        self.cur_slug = slug
        self.cur_title = title
        self._persist(last_slug=slug, last_title=title)   # v2.2.0：记住上次查看的型号
        self.cur_host = "com"          # 待查询结果确定（特供型号会落到 'cn'）
        # v2.3.1：顺序有讲究 —— 副标题（slug）与数据源徽章决定标题的**可用宽度**，
        # 必须先把它们摆好再算标题省略。反过来写（先算标题、后 set slug）时，
        # 让路决策是在副标题还空着的时候做出的：等 slug 撑宽 198px 之后没人再算，
        # 标题就被挤到 178px 而 slug 照常显示 —— 正好是让路顺序写反的效果。
        self.v_board_sub.set(slug)
        self.lbl_host.configure(text="")
        self._show_board_title(title)
        # v2.4.0：立刻切到「查询中」加载态（旧版右侧一片空白，只有状态栏一行字）
        self.groups = {}
        self.badges = []
        self.cur_items = []
        self._latest_iids = set()
        self._iid_item = {}
        self._hover_row = None
        self.tv.delete(*self.tv.get_children())
        if self.grow.winfo_manager():
            self.grow.pack_forget()
        if self._panel_note_box.winfo_manager():
            self._panel_note_box.pack_forget()
        self._start_loading(title)

    def _board_worker(self, slug, title):
        """后台查询 BIOS 面板。

        v2.0.0 修复：无论成功 / 失败都必须发 busy=False 解除主按钮禁用 ——
        旧版成功分支漏发，导致选完型号后「下载选中版本」永久停在 disabled 暗红。
        """
        try:
            panel, host = self.api.get_bios_panel(slug, "bios")
            if panel is None:
                self.q.put(("board", (slug, title, None, None,
                                      "官网无 BIOS 数据（可能尚未发布或型号有误）", host)))
                return
            groups, _os, note, _ptitle = self.api.parse_bios_groups(panel)
            if not groups:
                self.q.put(("board", (slug, title, None, None, "该型号 BIOS 列表为空", host)))
                return
            self.q.put(("board", (slug, title, groups, note, None, host)))
        except Exception as e:
            self.q.put(("board", (slug, title, None, None,
                                  "查询失败：%s" % str(e)[:300], "com")))
        finally:
            self.q.put(("busy", False))

    def _apply_board(self, data):
        slug, title, groups, note, err, host = data
        # v2.2.0：清在途标记 + 写内存缓存 —— 都放在「是否过期」判断**之前**：
        # 过期结果虽不上屏，但拿到的数据本身有效，缓存下来可供后续复用。
        self._panel_inflight.pop(slug, None)
        if groups is not None:
            self._panel_cache.put(
                slug, (time.time(), groups, note,
                       host if host in ("com", "cn") else "com"))
        if self._loading_slug == slug:      # 该型号查询已结束（成功/失败均清锁）
            self._loading_slug = None
        if slug != self.cur_slug:      # 过期结果，丢弃
            return
        self.cur_host = host if host in ("com", "cn") else "com"
        # v2.4.0：数据源徽章（栏 3 标题行右侧）—— 明确当前读的是全球站还是中国站
        # v2.5.2：徽章成为数据源的**唯一**承载者（状态栏右读数不再复述），
        # 措辞统一为「· 数据源：x」（原来是「· 数据源 x」，与状态栏的冒号写法不一致）。
        host_txt = "微星中国站" if self.cur_host == "cn" else "微星全球站"
        try:
            self.lbl_host.configure(text="· 数据源：%s" % host_txt)
        except Exception:
            pass
        # v2.3.1：徽章从空变成 138px 宽，标题的可用宽度随之变化 —— 必须重算一次，
        # 否则标题会按"徽章还不存在"时的宽度去省略（该省的不省）。
        self._fit_board_title()
        if groups is None:
            self._show_board_title(title)
            self.groups = {}
            self.badges = []
            self.cur_items = []
            self._latest_iids = set()
            self._iid_item = {}
            self.tv.delete(*self.tv.get_children())
            if self.grow.winfo_manager():
                self.grow.pack_forget()
            # v2.3.5：显示占位并保留型号标题/slug（仍可点「打开官网支持页」核实）
            # v2.5.5：占位里不再重复型号名 —— 标题区已经写着它了，同一张卡里
            # 上下一模一样的两个大字读起来像渲染出错。占位改说「结论 + 下一步」。
            self._show_empty(
                True, title="查询失败",
                sub=err or "没拿到该型号的 BIOS 列表。可点右上角「打开官网支持页」核实。",
                keep_title=True)
            self._set_status(err or "查询失败", "err")
            return
        self.groups = groups
        self.badges = list(groups.keys())
        # v2.5.5：官网页可能返回 downloads 有内容、但里面没有任何 BIOS 分组
        # （只剩驱动 / os 字段时 parse_bios_groups 得到 {}，注意**不是 None**）。
        # 旧代码下面直接 self.badges[0] → IndexError → 被 _dispatch 的 except 吞掉，
        # 界面永久停在"查询中"：不报错、不恢复、日志里只有一行 dispatch err。
        if not self.badges:
            self.cur_items = []
            self._latest_iids = set()
            self._iid_item = {}
            self.tv.delete(*self.tv.get_children())
            self.cur_badge = None
            if self.grow.winfo_manager():
                self.grow.pack_forget()
            self._show_board_title(title)
            self._show_empty(
                True, title="暂无可用 BIOS 数据",
                sub="官网该型号页面下没有公开的 BIOS 下载（当前数据源：%s）。" % host_txt,
                keep_title=True)
            self._set_status("暂无可用 BIOS 数据（数据源：%s）" % host_txt, "warn")
            return
        # 多分组才显示类型下拉
        if len(self.badges) > 1:
            self.grp_box["values"] = ["%s（%d 项）" % (b, len(groups[b])) for b in self.badges]
            self.grp_box.current(0)
            if not self.grow.winfo_manager():
                # v2.4.0 grid 布局：grow 放 _list_zone 顶部（rf row=2 内的 pack）
                self.grow.pack(fill="x", pady=(S(0), S(6)))
        else:
            if self.grow.winfo_manager():
                self.grow.pack_forget()
        self._load_badge(self.badges[0])
        # v2.5.1：主板级提示框**不再显示**（用户反馈）。
        # 它取自 panel 的 note 字段（官方 SOP / Bilibili 或 YouTube 教程 / 解压说明），
        # 原本 pack 在表格下方 —— 但视觉上紧贴表格最后一行，读起来像「混进列表的数据行」
        # （实测会把「Youtube: MSI® HOW-TO use M-FLASH for BIOS」这种文案渲染成一条列表项），
        # 干扰对 BIOS 行的扫读。控件与 StringVar 保留（便于以后改挂到设置面板等处），
        # 这里统一不 pack。
        self.v_panel_note.set("")
        if self._panel_note_box.winfo_manager():
            self._panel_note_box.pack_forget()
        self._set_status("%s · 共 %d 个 BIOS 版本%s" %
                         (title, len(self.cur_items),
                          "（数据源：微星中国站）" if self.cur_host == "cn" else ""), "ok")

    def _on_group_changed(self, _ev=None):
        i = self.grp_box.current()
        if 0 <= i < len(self.badges):
            self._load_badge(self.badges[i])

    def _load_badge(self, badge):
        self.cur_badge = badge
        items = list(self.groups.get(badge) or [])
        items.sort(key=lambda it: it.get("download_release") or "", reverse=True)
        self.cur_items = items
        self._hover_row = None
        self._latest_iids = set()
        self._iid_item = {}
        self.tv.delete(*self.tv.get_children())
        for i, it in enumerate(items):
            ver = clean_version(it.get("download_version"))
            # v2.4.0：最新版本在版本号前加 ★ 前缀。
            # 直接选中态会顶替 tag 的绿底（Treeview 的 selected map 永远覆盖 tag 颜色），
            # 视觉上像是"红色错误"。前缀字符即使在选中时也能让用户看出是最新行。
            # 复制菜单用 clean_version 拿原始值，菜单/匹配不受 ★ 影响。
            if i == 0:
                ver = "★ " + ver
            date = it.get("download_release") or ""
            size = it.get("download_size") or 0
            try:
                size = "%.1f MB" % (int(size) / 1048576.0)
            except Exception:
                size = ""
            desc = (it.get("download_description") or "").replace("\n", " ").strip()
            tag = ("latest", "row") if i == 0 else ("row",)
            iid = self.tv.insert("", "end", values=(ver, date, size, desc[:56]), tags=tag)
            self._iid_item[iid] = it
            if i == 0:
                self._latest_iids.add(iid)
        if items:
            self._show_empty(False)
            self._fade_list_in()        # v2.4.0：列表淡入
            first = self.tv.get_children()[0]
            self.tv.selection_set(first)
            self.tv.focus(first)
            self._fit_tv_height()       # v2.5.5：行数变了，重算可视行数
        else:
            self._show_empty(True)

    def _on_tv_double_click(self):
        if not self.tv.selection():
            return
        if self.dl_thread and self.dl_thread.is_alive():
            return
        self._on_download()

    # ------------------------------------------------------------- 官网页
    def _on_open_site(self):
        if self.cur_slug:
            host = CN_BASE if self.cur_host == "cn" else BASE
            webbrowser.open("%s/Motherboard/%s/support" % (host, self.cur_slug))
        else:
            webbrowser.open(BASE + "/Motherboards/Products")

    # ------------------------------------------------------------- 下载
    def _on_pick_dir(self):
        d = filedialog.askdirectory(title="选择 BIOS 文件保存目录",
                                    initialdir=self.last_dir or os.path.expanduser("~"))
        if d:
            self.last_dir = d
            self._set_dir_display(d)
            self._persist(last_dir=d)      # v2.2.0：记住保存目录

    def _default_dir(self):
        if self.last_dir:
            return self.last_dir
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        return dl if os.path.isdir(dl) else os.path.expanduser("~")

    # ------------------------------------------------- v2.5.0 选中版本详情
    def _on_detail_configure(self, _ev=None):
        """让「更新说明」的换行宽跟随**详情面板**宽度，而不是标签自己。

        这是切断布局反馈环的关键：若让 tk.Label 按自身内容决定换行宽，它的请求高
        会撑高详情区，详情区变高又改变可用宽度 —— 闭环。统一由容器宽度单向驱动，
        再叠加 DETAIL_MAX_LINES 的行数封顶，请求高才有确定上界。
        """
        try:
            w = self._detail_zone.winfo_width() - S(24) - S(2)
            if w > S(120):
                self._det_note.configure(wraplength=w)
        except Exception as _e:
            _log("detail wrap err: %r" % (_e,))

    def _det_btns_enabled(self, on):
        """详情槽两个控件的启用态与配色（v2.5.5）。

        tk.Button 把 state 设成 disabled 时**不会**自动改底色 —— 旧版详情槽在空状态下
        只是 `state="disabled"`，按钮仍是满血亮红，与底部真正可用的主按钮长得一模一样，
        点下去毫无反应。这里把禁用态显式压暗（底 C_BTN_DIS + 字 C_DIM）。
        """
        on = bool(on)
        try:
            self.btn_det_dl.configure(
                state=tk.NORMAL if on else tk.DISABLED,
                bg=C_BTN if on else C_BTN_DIS,
                fg=C_TEXT if on else C_DIM,
                activebackground=C_BTN_HOVER if on else C_BTN_DIS)
        except Exception as e:
            _log("det dl btn state err: %r" % (e,))
        try:
            self.btn_det_url.configure(
                state=tk.NORMAL if on else tk.DISABLED,
                fg=C_BLUE if on else C_DIM,
                disabledforeground=C_DIM)
        except Exception as e:
            _log("det url btn state err: %r" % (e,))

    def _sync_dl_btn(self):
        """底部主按钮的文案与启用态（v2.5.5）。

        文案跟着选中版本走：旧版恒为「下载选中版本」，与详情槽的「下载此版本」并排时
        用户没法判断两者的区别 —— 它们下的是同一个文件。现在主按钮直接写出版本号
        （「下载 7D89v1C2」），"选中版本"这个词就不需要再解释了。

        无选中 / 无下载链接 / 查询或下载在途 → 禁用，并把底色压暗一档。
        唯一写入口是这里，`_busy()` 只负责改 `_busy_flag` 再转调 —— 两处各写一套
        配色是"状态互相覆盖"的老来源。
        """
        try:
            # 建窗过程中 _show_empty(False) 可能早于 _ui_download_row 触发，
            # 此时 btn_dl 还不存在。这不是错误，是一个合法的中间态：
            # 控件没建好时同步没有意义，_ui_finish 末尾会补一次终态同步。
            # 不加这个守卫的话，每次启动都会往日志里写一行
            # "sync dl btn err: AttributeError(...)" —— 被 except 吞掉不影响
            # 运行，但天天写一次会把真错误淹掉（实测冒烟日志里就有这一行）。
            if not hasattr(self, "btn_dl") or self.btn_dl is None:
                return
            busy = bool(self._busy_flag) or self._inflight > 0
            it = None if busy else self._selected_item()
            ver = clean_version((it or {}).get("download_version"))
            ok = bool(it) and bool(it.get("download_url"))
            text = ("下载 %s" % ver) if (ok and ver) else "下载选中版本"
            if self.btn_dl.cget("text") != text:
                self.btn_dl.configure(text=text)
            self.btn_dl.configure(state=tk.NORMAL if ok else tk.DISABLED,
                                  bg=C_ACCENT_BTN if ok else C_ACCENT_BTN_DIS,
                                  disabledforeground=C_ACCENT_BTN_FG_DIS)
        except Exception as e:
            _log("sync dl btn err: %r" % (e,))

    def _show_detail(self, it):
        """把选中版本摊平显示在栏 3 底部详情面板；it 为 None 时显示引导占位。"""
        try:
            self._det_item = it
            if not it:
                self._det_ver.configure(text="—")
                self._det_meta.configure(text="")
                self._det_size.configure(text="")
                self._det_note.configure(
                    text="在上方列表里选中一个 BIOS 版本，"
                         "这里会显示它的完整更新说明与 SHA-256 校验值。")
                self._det_sha.configure(text="")
                self._det_btns_enabled(False)
                self._sync_dl_btn()
                return
            # 是不是「最新」那一版（与列表里的 ★ 前缀同源：_load_badge 里 i == 0）
            is_latest = False
            for iid, obj in self._iid_item.items():
                if obj is it:
                    is_latest = iid in self._latest_iids
                    break
            ver = clean_version(it.get("download_version"))
            self._det_ver.configure(text=("★ " if is_latest else "") + (ver or "—"))
            self._det_meta.configure(text=str(it.get("download_release") or "—"))
            sz = it.get("download_size") or 0
            try:
                sz_txt = "%.1f MB" % (int(sz) / 1048576.0)
            except (TypeError, ValueError):
                sz_txt = "—"
            self._det_size.configure(text=sz_txt)
            desc = (it.get("download_description") or "").replace("\r", " ").strip()
            desc = " ".join(desc.split())
            if not desc:
                desc = "（该版本官网未提供更新说明）"
            # 行数封顶：按实测宽度估算每行可容纳的字符数，超出以「…」收尾。
            # 不封顶就会回到那个反馈环（见常量区注释里华硕的实测记录）。
            wrapw = max(S(160), self._detail_zone.winfo_width() - S(26))
            per_line = max(8, int(wrapw / max(1, self._text_px("测"))))
            cap = per_line * DETAIL_MAX_LINES
            if len(desc) > cap:
                desc = desc[:cap - 1].rstrip() + "…"
            self._det_note.configure(text=desc)
            sha = parse_sha256_from_field(it.get("download_sha256"))
            self._det_sha.configure(
                text=("SHA-256: %s" % sha) if sha else "SHA-256: 官网未提供")
            has_url = bool(it.get("download_url"))
            # 下载中禁用「下载此版本」，与主按钮保持一致
            busy = bool(self.dl_thread and self.dl_thread.is_alive())
            self._det_btns_enabled(has_url and not busy)
            self._sync_dl_btn()
            # v2.5.5：说明文字换行数变了 → 详情区请求高变了 → 「放得下几行」也要跟着变。
            # 旧版只在卡片 <Configure> 时重算，切换选中项不会触发，于是表高停留在
            # 上一次算出的值：长说明撑高详情区后，详情区底部会被顶出卡片（实测 11px）。
            self._refit_tv_soon()
        except Exception as _e:
            _log("show detail err: %r" % (_e,))

    def _selected_item(self):
        """当前选中的 BIOS 条目（v2.0.0）。

        改为 iid → item 映射直查。旧版拿显示文本里的版本号回查 cur_items，
        遇到两条都缺版本号（clean_version 都返回「—」）时会取到错的那条；
        ★ 前缀也需要额外剥离，现在一并省掉。
        """
        sel = self.tv.selection()
        if not sel:
            return None
        return self._iid_item.get(sel[0])

    def _on_download(self):
        it = self._selected_item()
        if not it:
            messagebox.showwarning(APP_TITLE, "请先在列表中选择要下载的 BIOS 版本", parent=self.root)
            return
        if self.dl_thread and self.dl_thread.is_alive():
            messagebox.showwarning(APP_TITLE, "已有下载任务进行中", parent=self.root)
            return
        url = it.get("download_url")
        if not url:
            messagebox.showerror(APP_TITLE, "该版本缺少下载链接", parent=self.root)
            return
        fname = _safe_filename(url, clean_version(it.get("download_version")))
        save_dir = self._default_dir()
        self._set_dir_display(save_dir)
        if not self.last_dir:
            d = filedialog.askdirectory(title="选择 BIOS 文件保存目录", initialdir=save_dir)
            if not d:
                return
            self.last_dir = d
            self._set_dir_display(d)
            self._persist(last_dir=d)      # v2.2.0：记住保存目录
            save_dir = d
        dest = os.path.join(save_dir, fname)
        self.dl_cancel.clear()
        # v2.4.0：复位进度条配色 / 测速状态 / 旧横幅
        self._toast_hide()
        self._pb_color_reset()
        self.pb.set_idle(False)        # v2.5.5：让隐形的进度条显形
        self._dl_speed = None
        self._dl_last_t = None
        self._dl_last_b = 0
        # v2.0.0：先掐掉上一次的进度条补间再归零，否则旧动画会把 value 拉回去
        self.anim.cancel("pb")
        self._set_downloading(True)
        self.pb["value"] = 0
        self.v_pb.set("准备下载…")
        # v2.2.0：存在未完成分片时明确告知会续传（否则进度从中间开始会像 bug）
        _part = dest + ".part"
        if _part_size(_part) > 0:
            self.v_pb.set("发现未完成文件 %.1f MB，将从断点续传…"
                          % (_part_size(_part) / 1048576.0))
        ver = clean_version(it.get("download_version"))
        expect_sha = parse_sha256_from_field(it.get("download_sha256"))
        self._set_status("正在下载 %s（%s）…" % (fname, ver), "run")
        self.dl_thread = threading.Thread(target=self._dl_worker,
                                          args=(url, dest, expect_sha), daemon=True)
        self.dl_thread.start()

    def _dl_worker(self, url, dest, expect_sha):
        def cb(done, total):
            self.q.put(("dl_progress", (done, total)))
            return not self.dl_cancel.is_set()
        try:
            ok, path, err, sha = do_download(url, dest, progress_cb=cb,
                                             cancel_event=self.dl_cancel)
            # v2.2.0：摘要已在下载流内增量算出；仅当缺失（异常路径）才回退重读整文件
            if ok and expect_sha and not sha:
                self.q.put(("status", "下载完成，校验 SHA-256…", "run"))
                sha = sha256_file(dest)
            self.q.put(("dl_done", (ok, dest, err, sha, expect_sha)))
        except Exception as e:
            self.q.put(("dl_done", (False, dest, repr(e)[:200], None, expect_sha)))

    def _dl_progress(self, done, total):
        # v2.5.5：进度条空闲时是"隐形"的（槽画成卡片底色），开跑第一帧要让它显形
        self.pb.set_idle(False)
        # v2.4.0：速度 EMA + 剩余时间（旧版只有「已下载 / 总量」两个数字）
        now = time.monotonic()
        if self._dl_last_t is None:
            self._dl_last_t = now
            self._dl_last_b = done
        else:
            dt = now - self._dl_last_t
            if dt >= 0.35:
                inst = max(0.0, (done - self._dl_last_b) / dt)
                self._dl_speed = inst if self._dl_speed is None \
                    else 0.65 * self._dl_speed + 0.35 * inst
                self._dl_last_t = now
                self._dl_last_b = done
        if total > 0:
            pct = min(100.0, done * 100.0 / total)
            self._pb_set(pct)          # 缓动补间，不再整数跳变
            if self._pb_compact:
                # 窄窗口：只留速度 + 百分比，把宽度让给进度条本身
                if self._dl_speed and self._dl_speed > 1024:
                    self.v_pb.set("%s/s  %d%%" % (_fmt_bytes(self._dl_speed), int(pct)))
                else:
                    self.v_pb.set("%d%%" % int(pct))
            else:
                parts = ["%.1f / %.1f MB" % (done / 1048576.0, total / 1048576.0)]
                if self._dl_speed and self._dl_speed > 1024:
                    parts.append(_fmt_bytes(self._dl_speed) + "/s")
                    parts.append("剩 " + _fmt_eta((total - done) / self._dl_speed))
                parts.append("(%d%%)" % int(pct))
                self.v_pb.set("   ".join(parts))
        else:
            self.v_pb.set("%.1f MB" % (done / 1048576.0))

    def _dl_done(self, ok, path, err, sha, expect_sha):
        self._set_downloading(False)
        self._dl_speed = None
        self._dl_last_t = None
        if not ok:
            self._pb_color_reset()
            if err == "已取消":
                # v2.2.0：取消后保留 .part，下次点下载会从断点继续
                self._set_status("已取消下载（已保留断点，可再次点击继续）", "warn")
                self._toast_show("已取消下载 · 已保留断点，可续传", ok=False, ttl=6000)
                self.v_pb.set("")
                self.pb.set_idle(True)     # v2.5.5：取消后收回进度条
                return
            self._set_status("下载失败：%s" % err, "err")
            self._toast_show("下载失败：%s" % err, ok=False, ttl=12000)
            self.v_pb.set("")
            self.pb.set_idle(True)
            messagebox.showerror(
                APP_TITLE,
                "下载失败：%s\n\n已下载的部分已保留，再次点击下载将从断点续传。" % err,
                parent=self.root)
            return
        base = os.path.basename(path)
        msg = "下载完成：%s" % path
        if expect_sha and sha:
            if sha == expect_sha:
                msg += "\n\nSHA-256 校验：通过 ✓"
                self._set_status("下载完成，SHA-256 校验通过", "ok")
                self._toast_show("✓ 下载完成并校验通过    %s" % base)
            else:
                msg += "\n\n警告：SHA-256 校验不一致！\n期望 %s\n实际 %s" % (expect_sha, sha)
                self._set_status("下载完成，但 SHA-256 校验不一致！", "err")
                self._toast_show("⚠ SHA-256 校验不一致，请勿直接刷写    %s" % base,
                                 ok=False, ttl=15000)
        else:
            self._set_status("下载完成", "ok")
            self._toast_show("✓ 下载完成    %s" % base)
        self._pb_set(100, dur=220)
        self.v_pb.set("")
        messagebox.showinfo(APP_TITLE, msg, parent=self.root)
        # 弹窗关闭后再播完成动效，避免动画被模态窗口挡住
        self._pb_flash(C_ACCENT, C_OK)
        self._status_flash(C_OK)
        self.root.after(1400, self._pb_settle)

    def _on_cancel_download(self):
        """取消进行中的下载：置位 dl_cancel，下载线程轮询到后保留 .part 并回报。

        v2.2.0：改为保留分片 —— 这是断点续传的前提（旧版取消即删除，下次从头下）。
        """
        if self.dl_thread and self.dl_thread.is_alive():
            self.dl_cancel.set()
            self._set_status("正在取消下载…", "warn")
            try:
                self.btn_cancel.config(state=tk.DISABLED)
            except Exception:
                pass

    def _on_open_dir(self):
        d = self.last_dir or self._default_dir()
        try:
            if os.path.isdir(d):
                os.startfile(d)  # noqa  (Windows)
            else:
                messagebox.showwarning(APP_TITLE, "目录不存在：%s" % d, parent=self.root)
        except Exception as e:
            _log("open dir err %r" % (e,))
            messagebox.showwarning(APP_TITLE, "无法打开目录：%s" % d, parent=self.root)


# ================================================================ 自检（无 GUI）
def selftest():
    """--check: 控制台自检（打包后 stdout 不可见，写日志 + 输出到文件）。"""
    lines = []
    def p(m):
        lines.append(str(m))
        try:
            print(m)
        except Exception:
            pass

    p("=== MSI 主板 BIOS 下载工具 自检 v%s ===" % APP_VERSION)
    p("时间: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    api = MsiApi()

    # 1 目录接口
    p("\n[1] 官网目录接口")
    try:
        chipsets = api.get_chipset_tags()
        p("  芯片组分组合计: %d 组" % len(chipsets))
        for c in chipsets[:6]:
            p("    %s (id=%s)" % (c["title"], c["id"]))
        full = api.get_product_list(None)
        p("  全量在售型号: %d 款" % len(full))
    except Exception as e:
        p("  目录接口异常: %r" % (e,))

    # 2 目录构建（29 次芯片组请求）
    p("\n[2] 目录构建（Intel/AMD 归类）")
    try:
        cat = fetch_catalog(api, progress=lambda m: p("    " + m))
        save_catalog(cat)
        total = cat.get("total", 0)
        p("  总型号: %d" % total)
        for b in cat.get("brands") or []:
            p("  %s 主板: %d 款, %d 个芯片组" % (b["name"], b.get("count", 0), len(b.get("chipsets") or [])))
            for cs in (b.get("chipsets") or [])[:5]:
                p("      %s: %d 款（示例: %s）" % (cs["name"], len(cs["boards"]),
                                                    cs["boards"][0]["title"] if cs["boards"] else ""))
    except Exception as e:
        p("  目录构建异常: %r" % (e,))

    # 3 BIOS 面板
    p("\n[3] BIOS 面板（老型号 Z490 直查 + 中国站回退）")
    try:
        panel, host = api.get_bios_panel("MPG-Z490-GAMING-EDGE-WIFI", "bios")
        p("  数据源 host=%s" % host)
        groups, _os, note, title = api.parse_bios_groups(panel or {})
        p("  title=%r 分组=%s note=%r" % (title, list(groups.keys()), str(note)[:40]))
        for b, items in groups.items():
            p("  分组[%s] 共 %d 条" % (b, len(items)))
            for it in items[:3]:
                p("    ver=%-12s date=%s size=%s url=%s sha=%s" % (
                    it.get("download_version"), it.get("download_release"),
                    it.get("download_size"), str(it.get("download_url"))[:70],
                    "Y" if parse_sha256_from_field(it.get("download_sha256")) else "N"))
    except Exception as e:
        p("  面板异常: %r" % (e,))

    # 3b 中国站回退（大陆特供型号：全球站为空 -> 应落到 msi.cn）
    p("\n[3b] 中国站 BIOS 回退（B760M BOMBER WIFI）")
    try:
        panel, host = api.get_bios_panel("B760M-BOMBER-WIFI", "bios")
        groups, _os, note, title = api.parse_bios_groups(panel or {})
        n = sum(len(v) for v in groups.values())
        p("  host=%s 分组=%s 共 %d 条（期望 host=cn 且条数>0）" %
          (host, list(groups.keys()), n))
        for b, items in list(groups.items())[:1]:
            for it in items[:2]:
                p("    ver=%-12s url=%s" % (it.get("download_version"),
                                            str(it.get("download_url"))[:80]))
    except Exception as e:
        p("  中国站回退异常: %r" % (e,))

    # 4 下载直链连通性（DNS 自愈：download.msi.com 同为 Akamai 域）
    p("\n[4] 下载直链（HEAD/Range）")
    try:
        u = "https://download.msi.com/bos_exe/mb/7E48v1A75.zip"
        r = _cr_get_dns_safe(u, impersonate=IMPERSONATE, timeout=30,
                             headers={"Range": "bytes=0-255", "User-Agent": UA_CHROME})
        p("  %s -> HTTP %s, 收到 %d 字节, final=%s" % (
            u, r.status_code, len(r.content), r.url[:80]))
        r.close()
    except Exception as e:
        p("  直链异常: %r" % (e,))

    p("\n自检结束")
    txt = "\n".join(lines)
    try:
        out = os.path.join(_app_dir(), "msi_bios_checker_selftest.log")
        with open(out, "w", encoding="utf-8") as f:
            f.write(txt)
        p("（自检日志已保存: %s）" % out)
    except Exception:
        pass
    return 0


# ================================================================ main
# ---------------------------------------------------------------- DPI 说明（v2.0.0 审核）
# 本工具的字号与间距全部按「物理像素」标定（负值字号 = 像素，如 -17），视觉是在
# Windows **DPI 虚拟化**下校准的：进程不声明 DPI 感知 → 150% 缩放下 Windows 先按
# 96 DPI 渲染整窗、再放大 1.5×，于是 17px 字在屏幕上呈 25.5px，与设计一致。
# 若改为声明 Per-Monitor V2，Windows 不再放大位图，全部像素度量必须同步乘 DPI
# 系数，否则整体缩小 1/1.5 —— 属一次完整的度量重构，故此处显式保持现状。
# （旧版本这里有一个 _enable_dpi_awareness()，因 ctypes 作用域错误从未生效，
#   且 SetProcessDpiAwarenessContext 并不在 shcore.dll 中，属纯死代码，已移除。）


def main():
    if "--check" in sys.argv or "-c" in sys.argv:
        sys.exit(selftest())
    # v2.1.0：必须在创建 Tk 之前声明 DPI 感知 —— 否则 Tk 以 96 DPI 初始化，
    # 高缩放比下整个窗口被系统位图拉伸（文字发虚）。旧版把感知声明写成局部
    # ctypes 引用而从未生效，tk scaling 也错用了 DPI/96（应为 DPI/72）。
    aware = _init_dpi()
    try:
        # 先创建一个完整 Tk 走 tcl/tk 初始化，再创建 App
        root = tk.Tk()
        # 关键：构建期间窗口隐藏，构建完成再 deiconify 一次性显示完整 UI
        # —— 避免 Windows 在「Application Placeholder Window」阶段被截图
        root.withdraw()
        # 以窗口所在显示器的实际 DPI 校准（多屏混合 DPI 时比系统 DPI 更准）
        try:
            wdpi = int(ctypes.windll.user32.GetDpiForWindow(root.winfo_id()))
            if wdpi:
                # v2.2.1：**无条件**重算一次。模块级那次 _rebuild_fonts() 发生在 Tk
                # 创建之前，拿不到字族列表，只能走「首选字族」兜底；只有在真实 Tk 上
                # 重跑，_ui_font_family() 的探测与 DPI 校准才真正生效。
                _apply_dpi_scale(wdpi)
        except Exception:
            pass
        # tk scaling = 每磅像素数 = DPI/72（仅影响 pt 字号与少数控件内部度量；
        # 本程序字体为像素级负值，由 S() 缩放，不依赖此项）
        try:
            root.tk.call("tk", "scaling", _DPI / 72.0)
        except Exception:
            pass
        _log("dpi: aware=%s dpi=%d scale=%.3f work=%s" %
             (aware, _DPI, DPI_SCALE, _work_area()))
    except Exception as e:
        _log("tk init err: %r" % (e,))
        try:
            ctypes.windll.user32.MessageBoxW(0, "无法启动图形界面：%s" % e, APP_TITLE, 0x10)
        except Exception:
            pass
        sys.exit(1)
    try:
        App(root)
        root.update_idletasks()
        root.update()  # 先强制算一次 layout，让首帧一次画好
        # 让窗口出现在屏幕中央（必须 deiconify）
        root.deiconify()
        root.mainloop()
    except Exception as e:
        _log("app fatal: %r" % (e,))
        try:
            ctypes.windll.user32.MessageBoxW(0, "程序异常：%s" % e, APP_TITLE, 0x10)
        except Exception:
            pass


if __name__ == "__main__":
    main()
