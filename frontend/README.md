# Studio System Frontend

XMind 用例导图管理前端，基于 Vue 3 + Vite + Element Plus + Pinia + simple-mind-map。

## 功能

- 登录认证
- 平台管理（用户 / 角色 / 权限）
- 文件夹与导图管理
- 思维导图在线编辑（simple-mind-map）
- 版本历史
- **Wiki 文档系统**（基于 Git 的在线 Obsidian）
  - 知识库管理页 `/wiki`：卡片网格、新建（空库 / 远程克隆）、**导入本地库**（上传 zip 或服务器目录）、设置、pull/push、删除
  - 克隆/导入进度：卡片状态遮罩（不定进度条 + 阶段文案），自动轮询直至就绪；失败卡片显示原因
  - 全屏工作区 `/wiki/s/:vaultId`：文档树（过滤/右键操作）、多文档标签页、锁状态指示、提交/历史/图谱/搜索入口
  - Vditor 所见即所得编辑（IR 模式，本地 KaTeX）：输入防抖自动保存（30s）、Ctrl+S 保存、提交弹窗
  - `[[ ]]` 双链补全弹层（↑↓/Enter/Tab/鼠标选择，候选来自库内文档）
  - 图片/附件粘贴上传：自定义 upload handler，正文插入 `attachments/` 相对路径，渲染时 MutationObserver 重写为接口 URL
  - 关系图谱 `/wiki/s/:vaultId/graph`：ECharts 力导图（wiki 实线 / embed 虚线，按标签着色），全库/当前文档邻域切换，点击节点跳文档；无入链/出链的文档打开邻域时显示自身节点并提示「仅显示自身」，不再空白
  - 版本历史抽屉：提交列表、行级 diff、回滚
  - 只读模式：他人持锁时自动切换预览并显示「{用户名} 正在编辑」，15s 轮询等锁；锁释放后当前页自动恢复编辑并重新加锁；同账号另一窗口持锁时提示「本账号的另一窗口编辑中」
  - 搜索框 `#标签`（含全角 ＃）触发标签搜索，大小写不敏感
  - 双链点击跳转：编辑/预览两种模式下点击 `[[文档]]` 直接打开目标文档（Ctrl/Alt/Shift 组合键不拦截）；点击不存在的双链会询问是否创建，确认后自动建文档并打开
  - `[[` 补全弹层：候选列表不变时键盘 ↑/↓ 正常移动选中项（不会因 keyup 重建弹层跳回第一项）
  - 切页立即保存：切换标签/点击双链跳转前 flush 当前文档的防抖保存；标签切换去重，无重复请求
  - 锁生命周期：切换文档静默释放旧锁、关闭任意标签释放对应锁（不干扰当前页心跳）
  - 目录操作联动：删除文件夹强制关闭其下所有标签（不弹保存，避免重建已删文件）；移动文件夹/文档时同步改写已打开标签的路径
  - pull/push 错误提示：拉取冲突时弹窗列出冲突文件列表；推送被拒提示先拉取合并

## 任务模块（对齐主流待办应用）

`/task` 任务管理，UI 以主流待办应用桌面端为参照：

- **侧栏**：搜索（Ctrl K）、智能清单（今天/最近 7 天/收集箱/摘要）、视图（全部/日历/统计/习惯打卡/专注/四象限）、清单组（含颜色圆点与计数）
- **列表视图**：扁平任务行（无卡片边框/分隔线，行间留白 + 悬停浅灰底）；行内顺序 = 优先级竖条 → 标题 → 标签 → 右侧「清单名 + 日期（逾期红字）」
- **勾选框**：按视图区分形状（对齐主流待办应用）——清单列表/详情抽屉/看板 = 正圆；四象限 = 圆角方块，且逾期任务红框提示；已完成 = 主题色底白勾
- **快速添加**：底部输入条支持 `#清单` `!优先级` `@日期` `~标签` 快捷语法，回车保存
- **四象限**：整页 2×2 象限卡片（彩色徽标 + 标题），卡头悬停出 `＋/⋯`（新增走悬浮任务卡片，支持日期/旗标优先级/清单/标签）；支持时间/清单/优先级分组、排序、拖拽换象限；象限规则（参与清单、紧急天数）可配置，存 localStorage
- **详情抽屉**：右侧滑出，标题 + 日期/清单/标签 chips、富文本备注（支持待办 checkbox 行）、子任务、附件
- **日历/看板/时间线/统计/专注（番茄钟）/习惯打卡**：独立视图
- **搜索面板**：`Ctrl K`，`#标签`（含全角 ＃）触发标签搜索

## Wiki 路由

| 路径 | 页面 |
|------|------|
| `/wiki` | VaultManager 知识库管理 |
| `/wiki/s/:vaultId` | WikiWorkspace 全屏工作区 |
| `/wiki/s/:vaultId/graph` | GraphView 关系图谱 |

## 编辑器布局

编辑器 (`/case/editor/:mapId`) 采用 simple-mind-map 官方 web demo 风格的三栏布局：

```
┌─────────────────────────────────────────────────────────────┐
│  顶部工具栏（返回、撤销/重做、节点操作、保存/导出）             │
├──────┬──────────────────────────────────────┬───────────────┤
│      │                                      │               │
│ 左侧 │           画布区域                    │   右侧详情    │
│ 图标 │                                      │   面板        │
│ 边栏 │                                      │               │
│      │                                      │               │
│      ├──────────────────────────────────────┤               │
│      │           底部状态栏                  │               │
├──────┴──────────────────────────────────────┴───────────────┤
```

- **左侧图标边栏**：节点样式 / 基础样式 / 主题 / 结构 / 大纲 / 备注 / 图标 / AI / 版本 / 设置
- **右侧详情面板**：显示当前选中图标对应的功能面板
- **顶部工具栏**：返回、撤销/重做、插入节点、删除节点、图片/图标/超链接/备注/标签、概要/关联线/外框/公式、保存版本、导出

## simple-mind-map 插件

编辑器注册了以下插件：

```js
MindMap.usePlugin(Drag)
  .usePlugin(Select)
  .usePlugin(KeyboardNavigation)
  .usePlugin(MiniMap)
  .usePlugin(Export)
  .usePlugin(ExportPDF)
  .usePlugin(ExportXMind)
  .usePlugin(NodeBase64ImageStorage)
  .usePlugin(RichText)
  .usePlugin(AssociativeLine)
  .usePlugin(OuterFrame)
  .usePlugin(Formula)
  .usePlugin(RainbowLines)
  .usePlugin(Watermark)
  .usePlugin(NodeImgAdjust)
  .usePlugin(Search)
  .usePlugin(Painter)
  .usePlugin(Scrollbar)
  .usePlugin(TouchEvent)
  .usePlugin(MindMapLayoutPro)

Themes.init(MindMap)
```

## 浏览器 polyfill

`simple-mind-map` 依赖的 `xml-js` / `sax` 在浏览器端需要 Node 内置模块 polyfill。`vite.config.js` 已配置：

```js
resolve: {
  alias: {
    stream: resolve(__dirname, 'node_modules/stream-browserify'),
    events: resolve(__dirname, 'node_modules/events'),
    buffer: resolve(__dirname, 'node_modules/buffer'),
  },
},
define: {
  global: 'globalThis',
},
```

对应依赖：

```bash
npm install stream-browserify events buffer
```

## 启动

### 方式一：双击启动脚本（推荐本地开发）

```
studiosystem\frontend\start.bat
```

或一键启动前后端：

```
start-all.bat
```

### 方式二：命令行

```bash
# 1. 安装 simple-mind-map 依赖
cd ../mind-map/simple-mind-map
npm install

# 2. 安装前端依赖
cd ../../studiosystem/frontend
npm install

# 3. 启动开发服务器
npm run dev
```

## 构建

```bash
npm run build
```

默认代理到 `http://127.0.0.1:8302`。
