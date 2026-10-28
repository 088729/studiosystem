# Wiki 模块设计文档（前端篇）

> 覆盖：需求 · 前端架构 · 页面与交互设计 · API 封装
> 配套文档：`studiosystem/backend/Design/Wiki.md`（后台篇）
> 定位：基于 Git 的在线文档库（类 Obsidian），支持多库、双链、版本历史。

---

## 一、需求背景与目标

### 1.1 业务背景

将 Obsidian 的核心体验搬到线上：文档以 Git 仓库为底（版本可追溯、可同步远程），浏览器内完成编辑、双链、搜索、图谱。前端是本模块的主要载体。

### 1.2 核心目标

| 目标 | 说明 |
|------|------|
| 多库管理 | Vault 卡片列表，创建（空库/克隆远程）、设置、删除 |
| 文档浏览 | 左侧文档树（文件夹/文档），支持新建/重命名/移动/删除 |
| 在线编辑 | Vditor 所见即所得编辑，双链 `[[ ]]` 高亮与补全、`#标签`、数学公式、代码块、图片粘贴上传 |
| 版本历史 | 历史列表面板、版本间 diff 展示、一键回滚 |
| 双链 | 右侧反链面板、未解析链接提示、全局关系图谱页 |
| 搜索 | 顶栏全局搜索（标题/正文/标签），结果跳转定位 |
| 协作提示 | 编辑锁（他人编辑中提示 + 只读模式）、未提交变更提示、自动保存状态 |

### 1.3 模块边界

- **本模块负责**：Vault 管理页、编辑器、图谱、搜索、历史面板。
- **不在本模块**：实时协同光标、评论批注 UI、AI 助手面板（二期可扩展，接口已预留索引）。

---

## 二、总体架构

### 2.1 技术选型

| 关注点 | 选型 | 说明 |
|--------|------|------|
| Markdown 编辑器 | Vditor | 支持 WYSIWYG / 即时渲染 / 分屏三模式；内建代码高亮、数学公式（KaTeX 已有依赖）、大纲；可通过 `hl` 扩展双链高亮、自定义弹层做 `[[` 补全 |
| 图谱 | ECharts (graph series) | 节点拖拽、力导布局、点击跳文档、按标签着色 |
| diff 展示 | diff 纯文本后端返回 + 前端简单着色 | 不引 diff 库，按 `+`/`-`/`@@` 行级着色即可 |
| 状态管理 | Pinia `wikiStore` | 当前 Vault、文档树、打开标签页、锁状态、未提交变更数 |
| UI 组件 | Element Plus | 与全站一致；树、抽屉、对话框、消息提示 |

### 2.2 页面形态（对齐现有模块）

参考现有「用例管理」的二段式：**管理页带全局侧边栏，编辑器全屏**（`meta.hideSidebar`，CaseEditor 同款）。

| 页面 | 路由 | 形态 |
|------|------|------|
| Vault 管理页 | `/wiki` | 带全局侧边栏，卡片网格（视觉对齐 CaseManager） |
| 库工作区 | `/wiki/s/:vaultId` | **全屏**（hideSidebar）：自带顶栏 + 文档树 + 编辑区 + 右侧面板 |
| 关系图谱 | `/wiki/s/:vaultId/graph` | 全屏（hideSidebar），也可作工作区内抽屉打开 |

全屏工作区布局：

```
┌──────────────────────────────────────────────────────────┐
│ 顶栏：‹ 返回库列表 | 库名▾ | 模式切换 | 提交/历史/图谱/搜索 │
├──────────┬───────────────────────────────┬───────────────┤
│ 文档树    │  编辑区（Vditor）              │ 右侧面板       │
│ (可折叠)  │  - 标签页多开                  │ - 大纲         │
│          │  - 状态栏：保存态/锁            │ - 反链         │
│          │                               │ - 标签         │
└──────────┴───────────────────────────────┴───────────────┘
```

- 编辑器标签页多开（同库内多文档），切换标签触发自动保存。
- 右侧三面板可折叠；历史/提交以抽屉与对话框呈现，不占常驻布局。

---

## 三、前端设计

### 3.1 代码结构

```
src/views/wiki/
├── VaultManager.vue           # Vault 卡片管理页（创建/克隆/设置/删除；带全局侧边栏）
├── WikiWorkspace.vue          # 全屏工作区骨架（hideSidebar）：顶栏 + 文档树 + 编辑区 + 右侧面板
├── components/
│   ├── WikiSidebar.vue        # 左侧文档树（新建/重命名/移动/删除/拖拽排序）
│   ├── WikiEditorTabs.vue     # 中部标签页容器（多文档）
│   ├── WikiEditor.vue         # Vditor 封装：初始化/回填/防抖保存/锁交互
│   ├── WikiToolbar.vue        # 编辑区顶栏：模式切换/提交/历史/锁状态
│   ├── WikiRightPanel.vue     # 右侧容器：大纲/反链/标签
│   ├── OutlinePanel.vue       # 文档大纲（Vditor outline 或自解析）
│   ├── BacklinkPanel.vue      # 反链列表（点击跳源文档并滚动锚点）
│   ├── TagPanel.vue           # 当前文档标签（点击全局搜索该标签）
│   ├── HistoryDrawer.vue      # 版本历史 + diff 查看 + 回滚
│   ├── CommitDialog.vue       # 手动提交（自定义 message）
│   ├── GraphView.vue          # 关系图谱（全屏抽屉）
│   ├── SearchPanel.vue        # 全局搜索结果
│   └── VaultSettingsDialog.vue# 库设置（远程地址/自动提交/重建索引）
├── composables/
│   ├── useWikiEditor.js       # 编辑器生命周期：加载/防抖保存/锁心跳
│   ├── useWikiLock.js         # 加锁/续期/释放/轮询
│   └── useWikiTree.js         # 文档树数据与操作
├── utils/
│   └── wikiLink.js            # [[link]] 解析/补全过滤/路径归一（与后端同规则）
└── graph/
    └── graphOption.js         # ECharts graph 配置组装

src/api/wiki.js                # wiki 模块接口封装
src/stores/wiki.js             # Pinia：当前库/树/标签页/锁/未提交数
```

### 3.2 路由与权限

注册到 `src/router/index.js`（沿用现有 `meta.requiredPerm` / `hideSidebar` 模式）：

```js
{ path: '/wiki', component: () => import('@/views/wiki/VaultManager.vue'), meta: { requiredPerm: 'wiki:view' } },
{ path: '/wiki/s/:vaultId', component: () => import('@/views/wiki/WikiWorkspace.vue'), meta: { requiredPerm: 'wiki:view', hideSidebar: true } },
{ path: '/wiki/s/:vaultId/graph', component: () => import('@/views/wiki/components/GraphView.vue'), meta: { requiredPerm: 'wiki:view', hideSidebar: true } },
```

| path | component | 权限 | 形态 |
|------|-----------|------|------|
| `/wiki` | VaultManager.vue | wiki:view | 带侧边栏 |
| `/wiki/s/:vaultId` | WikiWorkspace.vue | wiki:view | **hideSidebar 全屏** |
| `/wiki/s/:vaultId/graph` | GraphView.vue | wiki:view | hideSidebar 全屏 |

**App.vue 菜单集成**（与用例/任务菜单并列）：

```vue
<el-menu-item index="/wiki" v-if="authStore.hasPerm('wiki:view')">
  <el-icon><Notebook /></el-icon>
  <template #title>知识库</template>
</el-menu-item>
```

- `activeMenu` 需补前缀匹配（现有代码只有 `/platform` 特例）：`if (route.path.startsWith('/wiki')) return '/wiki'`——空间/编辑器路由都让「知识库」菜单保持高亮。
- 图标只用 `@element-plus/icons-vue`（Notebook/Folder/DocumentAdd 等），与现有菜单/CaseManager 图标体系一致，不混用 lucide。
- 无 `wiki:view`：菜单不显示入口，直接访问由路由守卫跳 403（现有机制）。
- `wiki:edit` 控制编辑器可写、锁交互、新建/移动入口；`wiki:delete` 控制删除菜单；`wiki:manage` 控制「新建库 / 库设置 / 删除库 / 同步远程」按钮（`v-auth` 指令）。
- 只读模式：后端返回锁被占或用户无 `wiki:edit` 时，Vditor 切 `preview` 模式，工具栏隐藏编辑操作。

**样式约定**：全部复用 App.vue 暴露的 `--ss-*` 设计 token（`--ss-primary`、`--ss-bg`、`--ss-border`、`--ss-radius`、`--ss-shadow` 等）；页面滚动发生在内部容器（`html,body` 全站 `overflow:hidden` 的约定不能破坏）；消息提示统一 `ElMessage`（request.js 已统一拦截）。

### 3.3 API 封装

`src/api/wiki.js`：

| 函数 | 方法/路径 |
|------|-----------|
| `fetchVaults` / `createVault` / `fetchVault` | GET/POST/GET `/wiki/vaults` |
| `updateVault` / `deleteVault` | PATCH/DELETE `/wiki/vaults/{vid}` |
| `pullVault` / `pushVault` | POST `/wiki/vaults/{vid}/pull` / `push` |
| `fetchPageTree` | GET `/wiki/vaults/{vid}/pages/tree` |
| `fetchPageContent` | GET `/wiki/vaults/{vid}/pages/content?path=` |
| `createPage` / `savePage` / `deletePage` / `movePage` | POST/PUT/DELETE/POST `/wiki/vaults/{vid}/pages...` |
| `commitVault` | POST `/wiki/vaults/{vid}/pages/commit` |
| `lockPage` / `unlockPage` | POST/DELETE `/wiki/vaults/{vid}/pages/lock` |
| `fetchHistory` / `fetchDiff` / `revertPage` | GET/GET/POST `/wiki/vaults/{vid}/history...` |
| `searchPages` / `fetchBacklinks` / `fetchGraph` | GET `/wiki/vaults/{vid}/explore/...` |
| `rebuildIndex` | POST `/wiki/vaults/{vid}/explore/rebuild-index` |

### 3.4 VaultManager 管理页

带全局侧边栏进入，主体为卡片网格（白底、`--ss-radius`、`--ss-shadow`，视觉与 CaseManager 面板一致）。每张卡片：库名、描述、文档数、未提交变更徽标、最近更新时间、远程地址图标（已配置/未配置）。

- **新建库**：`el-dialog` → 库名 + 描述 + 可选远程地址（`remote_url`，留空即空库）。
- **克隆中状态**：创建后若后端返回「索引构建中」，卡片显示 `el-progress`，前端轮询 `fetchVault` 直至就绪（与后端 202 任务式语义配合）。
- **库操作菜单**：设置（`v-auth="'wiki:manage'"`）、同步远程（pull/push）、删除（`el-message-box` 二次确认，提示磁盘保留 30 天）。
- 卡片点击进入 `/wiki/s/:vaultId`。
- 空状态：`el-empty` + 「新建文档库」引导按钮（对齐现有空列表页做法）。

文档树交互（WikiSidebar，工作区内）对齐 CaseManager 的 tree-panel 习惯：
- 面板头：`toolbar-title`（图标 + 「文档」）+ 右侧图标按钮组（新建文档/新建目录，`v-auth` 控制）
- 面板头下方 `el-input size="small"` 过滤树；`el-tree` 高亮当前、图标区分文件夹/文档
- 节点右键 `el-dropdown` 菜单：新建/重命名/移动/删除（删除走 `el-message-box` 确认）

### 3.5 WikiWorkspace 全屏工作区

`hideSidebar` 全屏页（对齐 CaseEditor 的沉浸编辑模式），自带顶栏：返回库列表、库名下拉（切换/设置）、编辑模式切换、提交按钮、历史/图谱/搜索入口、锁状态指示。

**文档树（WikiSidebar）**：
- 数据来自 `fetchPageTree`，前端组装为 Element Plus `el-tree`（`props: {label: 'title'}`，图标区分文件夹/文档）。
- 节点操作右键菜单：新建文档/子目录、重命名、移动（弹窗选目标目录）、删除（二次确认）、复制路径。
- 拖拽移动：同库内 `movePage`，文件夹递归确认。
- 未提交变更的文档显示圆点标记（来自 Vault `status` 接口，进入时拉取一次，保存本地增量维护）。

**标签页（WikiEditorTabs）**：
- 同库多文档标签页；`keep-alive` 缓存编辑实例，切换标签 `before-leave` 触发当前文档保存。
- 关闭标签若内容未保存，弹确认。
- 路由 `:path` 与活动标签双向同步（浏览器前进/后退可用）。

**右侧栏**：
- **大纲**：读取 Vditor 大纲或自解析 H1-H3，点击滚动定位。
- **反链**：`fetchBacklinks(path)` 列表；点击项跳源文档（新标签），若有 `#锚点` 滚动至对应标题。
- **标签**：展示当前文档标签，点击进入全局搜索该标签。

### 3.6 WikiEditor 编辑器

**Vditor 初始化**：

```js
new Vditor(el, {
  mode: 'ir',                          // 默认即时渲染；工具栏可切 wysiwyg / ir / sv
  cache: { enable: false },            // 关闭本地缓存，统一走后端
  preview: {
    markdown: { mark: true },
    math: { engine: 'KaTeX' },
  },
  toolbar: [..., 'wiki-commit', 'wiki-history'],   // 自定义按钮
  after: () => editor.setValue(content),
})
```

**双链增强**：
- `input` 监听 `[[` 触发补全弹层：候选来源 `fetchPageTree` 本地过滤 + `searchPages`，显示「标题 + 路径」；`Enter` 插入 `[[目标|别名]]`。
- 即时渲染模式下通过自定义 render 或 CSS 高亮 `.vditor-ir__link[data-type="wiki"]`；预览模式渲染为库内跳转链接（点击新开标签读目标文档）。
- `![[embed]]` 预览模式渲染为目标文档内容摘要（二期；一期显示为可点击卡片）。

**图片/附件**：粘贴/拖拽图片 → 上传到资源平台 → 正文插入 `![name](attachments/xxx.png)` 相对路径（与后端约定一致）。

**保存策略（useWikiEditor）**：

| 触发 | 动作 | UI 反馈 |
|------|------|---------|
| 编辑输入 | 防抖 30s（可配） | 状态栏「保存中… → 已保存 HH:mm」 |
| 切换标签/关闭页/路由离开 | 立即保存 | beforeunload 兜底提示 |
| 手动 Ctrl+S / 提交按钮 | 保存 + `commitVault(message)` | 弹 CommitDialog；成功后未提交徽标清零 |

**编辑锁（useWikiLock）**：进入编辑即 `lockPage`；30s 心跳续期；被占时（409）切换只读并显示「{用户名} 正在编辑」+ 15s 轮询等待；释放随页面关闭/切文档。

### 3.7 版本历史（HistoryDrawer）

- 触发：工具栏「历史」按钮 → 抽屉从右滑出。
- 列表：`fetchHistory` 展示提交 message、作者、时间；空 message 的自动提交聚合为「自动保存快照」。
- diff：点击版本 → `fetchDiff` 行级着色展示（`+`绿 `-`红 `@@`灰），支持「与上一版本 / 与最新」切换。
- 回滚：当前版本旁「回滚到此版本」→ 二次确认（提示将产生新提交）→ `revertPage` → 刷新编辑器内容并 toast。

### 3.8 关系图谱（GraphView）

- 数据 `fetchGraph` → ECharts graph：节点=文档（标题，按首标签着色），边=链接（wiki 实线 / embed 虚线）。
- 交互：拖拽物理布局、滚轮缩放、点击节点跳文档（新标签）、hover 高亮相邻；支持「仅当前文档邻域 / 全库」切换。
- 大库性能：节点 >500 时默认展示当前文档 1 跳邻域 + 侧边栏搜索定位。

### 3.9 全局搜索（SearchPanel）

- 顶栏搜索框（Ctrl+K 唤起）：输入防抖 300ms 调 `searchPages`。
- 结果分组：标题命中 / 正文命中 / 标签命中；正文命中显示 ±40 字符片段并高亮关键词。
- Enter 跳第一个结果；点击条目新标签打开并滚动定位。

---

## 四、状态管理（Pinia `wikiStore`）

```js
state: {
  vaults: [],            // 库列表
  currentVault: null,    // 当前库详情（含 status）
  tree: [],              // 文档树（当前库）
  tabs: [],              // 打开标签 [{path, title, dirty, savedAt, lockState}]
  activeTab: '',
  backlinks: [],         // 当前文档反链
  graph: null,           // 图谱缓存
  unreadCommits: 0,      // 未提交数
}
```

- `openPage(path)`：命中已开标签则激活，否则追加并加载内容。
- `markDirty(path)` / `markSaved(path)`：维护未提交徽标。
- `refreshTree()`：操作后局部刷新树，避免全量拉取。

---

## 五、与现有模块的关系

| 模块 | 关系 |
|------|------|
| auth/platform | 复用权限键体系，新增 `wiki:view/edit/delete/manage`；`v-auth` 指令控制按钮 |
| resourceplatform | 附件上传复用其文件服务；附件相对路径写入正文，随 Git 提交 |
| case / task | 无耦合；任务/用例后续可在详情里以 `[[wiki:xxx]]` 形式引用文档（三期再做跳转协议） |

---

## 六、注意事项

1. **路由 path 编码**：文档路径含 `/` 与中文，入参一律 `encodeURIComponent`，路由解析后 decode 再传 API。
2. **锁与标签页**：多标签打开同一文档仅一个可写实例；重复打开复用并提示「已在编辑」。
3. **防抖保存取消**：组件卸载/切换文档时 `cancelDebounce` 并先 flush 保存，避免竞态丢内容。
4. **diff 大文本**：diff 结果 >5000 行后端截断，前端提示「仅展示部分内容」。
5. **Vditor 中文输入**：即时渲染模式在部分输入法组合中需处理 compositionend 后再触发保存，已在 `useWikiEditor` 用 `compositionend` 事件兜底。
6. **浏览器刷新**：刷新前若 `dirty` 未保存，本地 `beforeunload` 拦截提示（后端自动保存兜底）。
7. **图谱内存**：ECharts 实例在抽屉关闭时 `dispose()`，防止多实例内存泄漏。
8. **e2e 可测钩子**：项目有 `.uitest` 自动化习惯（App.vue 有 `window.__lastWebNotify` 先例）。编辑器暴露 `window.__wikiEditorState = { vaultId, path, savedAt, dirty, lockedBy }`，保存/提交/回滚后同步更新，供 UI 测试断言。
9. **不破坏全站滚动约定**：`html, body` 是 `overflow: hidden`，工作区与文档树的滚动必须发生在各自的内部容器（与 task/case 页面一致），否则 teleported 弹层会撑出双滚动条。

---

## 附录：后台接口速查

### Vault（`/wiki/vaults`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/wiki/vaults` | 列表 |
| POST | `/wiki/vaults` | 创建/克隆（body: name/description/remote_url） |
| GET | `/wiki/vaults/{vid}` | 详情 + status |
| PATCH | `/wiki/vaults/{vid}` | 设置 |
| DELETE | `/wiki/vaults/{vid}` | 删除（?hard=true 物理删） |
| POST | `/wiki/vaults/{vid}/pull` / `push` | 远程同步 |

### 页面（`/wiki/vaults/{vid}/pages`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `.../pages/tree` | 目录树 |
| GET | `.../pages/content?path=` | 读文档 |
| POST | `.../pages` | 新建 |
| PUT | `.../pages/content` | 保存（自动） |
| DELETE | `.../pages?path=` | 删除 |
| POST | `.../pages/move` | 移动/重命名 |
| POST | `.../pages/commit` | 提交变更 |
| POST/DELETE | `.../pages/lock` | 编辑锁 |

### 历史 / 探索（`/wiki/vaults/{vid}`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `.../history?path=` | 版本列表 |
| GET | `.../history/diff?path=&commit=` | diff |
| POST | `.../history/revert` | 回滚 |
| GET | `.../explore/search?q=` | 搜索 |
| GET | `.../explore/backlinks?path=` | 反链 |
| GET | `.../explore/graph` | 图谱 |
| POST | `.../explore/rebuild-index` | 重建索引 |

### 错误码速查

`wiki_path_invalid` / `wiki_vault_not_found` / `wiki_page_not_found` / `wiki_page_exists` / `wiki_locked`(409) / `wiki_remote_error`(502) / `wiki_rebuild_running`(202)
