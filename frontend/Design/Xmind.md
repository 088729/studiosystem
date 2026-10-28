# XMind 模块设计文档（前端篇）

> 覆盖：需求 · 前端设计 · 接口速查 · 权限
> 范围限定：仅保留「目录页」（文件夹管理）与「XMind 页」（导图编辑），去掉用例执行、用例记录、TAPD、飞书、LDAP 等非核心联动。

---

## 一、需求背景与目标

### 1.1 业务背景

测试团队用 XMind 思维导图编写测试用例。传统本地 `.xmind` 文件存在协作困难、版本丢失等问题。本模块将 XMind 用例**在线化**，沉淀到平台，作为用例编写的源头数据。

### 1.2 核心目标

| 目标 | 说明 |
|------|------|
| 在线编辑 | 基于 simple-mind-map 在浏览器中编辑用例导图，替代本地 XMind 客户端 |
| 结构化用例 | 导图节点带类型（功能/操作序列/输入/预期结果/说明） |
| 版本管理 | 草稿自动保存 + 手动快照 + 历史回滚，不丢内容 |
| 协作互斥 | 编辑锁防止多人同时改同一张导图 |
| 资产托管 | 节点图片上传到文件服务器，禁止 Base64 入库 |
| 导入兼容 | 支持批量导入存量 `.xmind` 文件 |
| 权限分级 | 查看 / 编辑 / 删除 / 管理四档权限 |

### 1.3 模块边界

- **本模块负责**：用例导图的文件夹组织、编辑、版本、资产、导入。
- **不在本模块**：用例执行、用例记录、TAPD/飞书/LDAP 等外部联动。

---

## 二、总体架构

### 2.1 技术选型

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + Beanie（MongoDB ODM） |
| 前端 | Vue 3 + Element Plus + simple-mind-map |
| 文档库 | MongoDB（4 个集合） |
| 文件存储 | resourceplatform 文件服务（SMB 共享），存图片等二进制 |

## 四、用例节点结构规范

> **已变更**：节点类型（`node_type`）功能已删除，连带移除右键菜单“设置节点类型”、大纲/画布类型 tag、结构校验和 `case_count` 用例数统计。节点数据只保留 `text`/`uid`/`expand` 等通用字段；存量数据中的 `node_type`/`tag` 字段为无害残留，无需迁移。Markdown 导入仍会识别并剥离 `[feat]`/`[input]` 等行内标记，但不再写入 `node_type`。

---

## 七、前端设计

前端仓库：`SunWeb/suntestplatformfront`（Vue 3 + Element Plus + Vite + Pinia）。

### 7.1 代码结构

```
src/views/case/
├── CaseManager.vue            # 管理页：三栏布局（层级/详情/预览）
├── CaseEditor.vue             # 编辑器主体
├── CaseEditorToolbar.vue      # 顶部工具栏
├── CaseEditorSidebar.vue      # 右侧侧边栏
├── CaseEditorStatusBar.vue    # 底部状态栏
├── CaseEditorContextMenu.vue  # 画布右键菜单
├── CaseEditorIconToolbar.vue  # 节点图标内联气泡
├── CaseEditorTagPopup.vue     # 节点标签内联气泡
├── panels/                    # 侧边栏 Tab 面板
│   ├── NodeStylePanel.vue
│   ├── BaseStylePanel.vue
│   ├── ThemePanel.vue
│   ├── StructurePanel.vue
│   ├── OutlinePanel.vue
│   ├── OutlineNode.vue
│   ├── NotePanel.vue
│   ├── IconPanel.vue
│   └── AiChatPanel.vue
└── dialogs/
    ├── NodeImageDialog.vue
    ├── NodeLinkDialog.vue
    ├── NodeNoteDialog.vue
    ├── NodeTagDialog.vue
    ├── NodeIconDialog.vue
    └── NodeImgToolbar.vue

src/api/case.js                # case 模块接口封装
src/utils/aiMarkdown.js        # Markdown → 节点树解析器
src/utils/imgClipboard.js      # 节点图片剪贴板
```

### 7.2 路由与权限

| path | name | component | 权限 |
|------|------|-----------|------|
| `case` | case | CaseManager.vue | xmind:view |
| `case/editor/:mapId` | case-editor | CaseEditor.vue | xmind:view |

版本预览通过 query 参数 `?version=N` 进入只读模式。

**框架骨架**：

- 应用启动：`createApp` → `app.use(pinia)` → `app.use(router)` → `app.use(ElementPlus)` → 全局注册 `v-auth` 权限指令 → `Themes.init(MindMap)` → `mount('#app')`
- HTTP 实例：`axios.create`，请求拦截自动带 `Authorization: Bearer {token}`；响应拦截 `res => res.data`
- Vite proxy：`/api`、`/static` 代理到后端

### 7.3 API 封装

`src/api/case.js`：

| 函数 | 方法/路径 |
|------|-----------|
| `fetchFolderTree()` | GET `/folders/tree` |
| `createFolder` / `renameFolder` / `moveFolder` / `deleteFolder` | POST/PATCH/PATCH/DELETE `/folders...` |
| `fetchMaps` / `fetchMap` / `createMap` | GET/GET/POST `/maps...` |
| `saveDraft` / `renameMap` | PATCH `/maps/{id}` |
| `deleteMap` / `moveMap` | DELETE `/maps/{id}` / PATCH `/maps/{id}/folder` |
| `fetchVersions` / `fetchVersion` | GET `/maps/{id}/versions...` |
| `createSnapshot` | POST `/maps/{id}/snapshot` |
| `copyMap` / `rollbackVersion` | POST `/maps/{id}/copy` / `/rollback` |
| `checkHash` / `uploadAsset` / `deleteAsset` | POST/POST/DELETE `/assets...` |
| `lockMap` / `unlockMap` | POST/DELETE `/maps/{id}/lock` |

### 7.4 CaseManager 管理页

三栏 flex 布局：层级 20%、详情 30%、预览 50%。

- **文件树**：`loadTree()` 并发拉取文件夹与各文件夹下导图，前端组装树
- **文件夹/导图操作**：新建/重命名/移动/删除/复制
- **拖拽**：原生 HTML5 DnD，支持文件夹环检测、map 移动、外部 `.xmind`/`.md`/`.json` 导入
- **复制/剪切/粘贴**：Ctrl+C/X/V
- **预览面板**：只读 MindMap 预览
- **详情面板**：显示 owner/created_at/last_modified_at/current_version，有草稿时提示恢复

### 7.5 CaseEditor 编辑器

**simple-mind-map 插件**：Drag、Select、KeyboardNavigation、MiniMap、Export、ExportPDF、ExportXMind、NodeBase64ImageStorage。

**关键 state**：`mindMap`、`mapTitle`、`isReadonly`、`canEdit`、`draftDirty/draftSaved`、`canUndo/canRedo`、`lockedByOther/lockedByName`。

**初始化流程**：

```
previewVersionNo? → fetchVersion(mapId, N)
否则 → fetchMap(mapId)
  ├─ 有 xmind:edit → lockMap(mapId)
  │    ├─ 成功 → startLockHeartbeat()
  │    └─ 423 → lockedByOther=true + startLockPoll()
  ├─ temp_content && canEdit → 弹框"恢复草稿"
  └─ 无草稿 → rootData = latest_root
```

**数据保存**：

| 触发 | 接口 | 说明 |
|------|------|------|
| `data_change` 防抖 2s | PATCH `/maps/{id}` | 草稿自动保存 |
| 用户点"保存版本" | POST `/maps/{id}/snapshot` | 手动快照 |

**编辑锁**：30s 心跳续期；只读者 15s 轮询；关闭时释放。

**图片处理**：`uploadImgMapAndClean` 将 base64 转文件上传，用返回 URL 替换；支持图片剪贴板复制/剪切/粘贴。

---

## 九、simple-mind-map 数据结构

存入 `case_versions.root` 的顶层结构：

```json
{
  "root": {
    "data": { "text": "根节点", "uid": "root", "expand": true },
    "children": [ ... ]
  },
  "layout": "logicalStructure",
  "theme": { "template": "default", "config": {} },
  "view": { "transform": { "scale": 1, "x": 0, "y": 0 } }
}
```

节点 `data` 字段：

| 字段 | 说明 |
|------|------|
| `text` | 节点文本（**必须字符串，不可 null/undefined**） |
| `uid` | 节点唯一标识，资产关联与增量更新关键 |
| `tag` | 标签数组（用户手动设置，通用标签） |
| `expand` | 子节点是否展开 |
| `image` | 图片绝对 URL（禁止 Base64） |
| `icon` | 图标 key 数组，格式 `["type_name"]` |
| `note` | 备注文本 |
| `hyperlink` | 超链接 URL |
| `imgMap` | 图片 key→URL 映射 |

---

## 十、注意事项

| # | 事项 |
|---|------|
| 1 | 编辑锁超时为 **1 分钟**，靠草稿保存/心跳刷新 `locked_at` 续期 |
| 2 | 资产去重用 **MD5** |
| 3 | 草稿保存接口立即返回，实际写入异步；版本快照才是权威持久化 |
| 4 | ~~`node_type` 为单一数据源~~（节点类型功能已删除） |
| 5 | 预览容器不可 `v-show` 隐藏，否则 MindMap 取不到宽高报错 |
| 6 | 节点 `text` 必须为字符串，`sanitizeNode()` 兜底防止后端 `None`→JSON `null` 触发编辑报错 |
| 7 | 文件夹删除是级联物理删除文件夹 + 软删除导图 |
| 8 | ~~快照结构校验为阻断性（422）~~（已随节点类型功能一并删除） |

---

## 十一、用户与权限模块（前端部分）

#### 代码结构

```
src/views/auth/
├── LoginView.vue              # 登录页
├── UserProfile.vue            # 个人中心 / 修改工作职能
└── admin/
    ├── UserManager.vue        # 用户管理（列表 + 权限编辑）
    ├── RoleManager.vue        # 角色管理
    └── PermissionManager.vue  # 权限 key 管理

src/views/platform/
└── PlatformAdmin.vue          # 平台管理入口（Tab：用户/角色/权限）

src/api/auth.js                # 登录、用户信息、用户/角色/权限管理接口
src/stores/auth.js             # Pinia：token、用户信息、权限计算
src/directives/auth.js         # v-auth 权限指令
src/router/guards.js           # 路由守卫：登录检查 + requiredPerm 检查
```

#### 路由与权限

| path | component | meta.requiredPerm |
|------|-----------|-------------------|
| `/login` | LoginView.vue | — |
| `/profile` | UserProfile.vue | 登录即可 |
| `/platform/admin` | PlatformAdmin.vue | `sys:manage` |

路由守卫逻辑：
1. 无 token 且访问非公开页 → 跳 `/login` 并带 `redirect` 参数
2. 页面配置了 `meta.requiredPerm` → 调用 `authStore.hasPerm(perm)`，无权限跳 403 或 summary 页
3. 已登录访问 `/login` → 跳首页

#### 状态管理（authStore）

```javascript
// src/stores/auth.js
const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sun_access_token'))
  const userInfo = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const perms = computed(() => userInfo.value?.perms || [])

  function hasPerm(perm) {
    if (!perm) return true
    const list = perms.value
    return list.includes('*') || list.includes(perm)
  }

  async function login(username, password, rememberMe = false) {
    const res = await authApi.login({ username, password, remember_me: rememberMe })
    setToken(res.access_token, rememberMe)
    await fetchMe()
    return res
  }

  async function fetchMe() {
    userInfo.value = await authApi.getMe()
  }

  function logout() {
    token.value = null
    userInfo.value = null
    localStorage.removeItem('sun_access_token')
    sessionStorage.removeItem('sun_access_token')
    router.push('/login')
  }

  return { token, userInfo, isLoggedIn, perms, hasPerm, login, fetchMe, logout }
})
```

#### 登录页（LoginView.vue）

- 表单：用户名、密码、记住我（remember_me）
- 调用 `authStore.login`
- 成功：从 URL 取 `redirect` 回跳，否则跳 `/case`
- 失败：显示后端返回错误（401/403）

#### 权限指令（v-auth）

```javascript
// src/directives/auth.js
export default {
  mounted(el, binding) {
    const authStore = useAuthStore()
    if (!authStore.hasPerm(binding.value)) {
      el.parentNode?.removeChild(el)
    }
  }
}
```

用法：`<el-button v-auth="'sys:manage'">删除</el-button>`

#### 平台管理页（PlatformAdmin.vue）

Tab 切换三栏：用户管理 / 角色管理 / 权限管理。仅 `sys:manage` 可访问。

**用户管理（UserManager.vue）**

- 表格列：用户名、姓名、部门、角色、是否在职、最近登录、操作
- 顶部搜索：按用户名/姓名模糊搜索
- 操作按钮：
  - 编辑权限 → Dialog：角色下拉 + extra 权限多选 + denied 权限多选
  - 禁用/启用账号
  - 删除本地记录（下次登录以 viewer 重建）
- 批量操作：选中多用户后批量改角色/批量禁用

**角色管理（RoleManager.vue）**

- 表格列：角色名、描述、权限数、是否内置、操作
- 新建角色：名称 + 描述 + 权限多选（从 `/auth/permissions` 拉取 key 列表）
- 编辑角色：全量替换 permissions/description
- 删除角色：内置角色禁用删除，被用户引用时提示

**权限管理（PermissionManager.vue）**

- 表格列：权限 key、是否内置、操作
- 新增权限 key：输入 key 名称，用于后续自定义扩展
- 删除权限 key：内置 key 不可删

#### API 封装（src/api/auth.js）

| 函数 | 方法/路径 |
|------|-----------|
| `login(data)` | POST `/common/auth/login` |
| `getMe()` | GET `/common/auth/me` |
| `getUsers(params?)` | GET `/common/auth/users` |
| `updateUserPermissions(username, data)` | PATCH `/common/auth/users/{username}/permissions` |
| `batchUpdatePermissions(data)` | POST `/common/auth/users/batch-permissions` |
| `setUserActive(username, data)` | PATCH `/common/auth/users/{username}/active` |
| `deleteUser(username)` | DELETE `/common/auth/users/{username}` |
| `updateJobScope(username, data)` | PATCH `/common/auth/users/{username}/job-scope` |
| `getRoles()` | GET `/common/auth/roles` |
| `createRole(data)` | POST `/common/auth/roles` |
| `updateRole(name, data)` | PATCH `/common/auth/roles/{name}` |
| `deleteRole(name)` | DELETE `/common/auth/roles/{name}` |
| `getPermissions()` | GET `/common/auth/permissions` |
| `createPermission(data)` | POST `/common/platform/permissions` |
| `deletePermission(key)` | DELETE `/common/platform/permissions/{key}` |

#### 与个人中心的联动

- 顶部导航头像下拉 → "个人中心" 跳 `/profile`
- 个人中心展示：用户名、姓名、邮箱、部门、角色、权限列表、工作职能
- 工作职能仅本人可编辑，调用 `updateJobScope`

### 11.7 关键流程时序

#### 登录流程

```
用户填写账号密码
  → POST /common/auth/login
    → 后端认证并签发 JWT
    → 返回 { access_token, token_type, expires_in }
  → 前端存 token
  → GET /common/auth/me 拉取用户信息和 perms
  → 跳转目标页 /case
```

#### 权限校验流程

```
用户进入 /platform/admin
  → 路由守卫检查 token
  → 检查 meta.requiredPerm = "sys:manage"
  → authStore.hasPerm("sys:manage") ? 放行 : 跳转无权限页
```

#### 给用户授权流程

```
管理员打开用户管理
  → 点"编辑权限"
  → Dialog 加载当前角色 + extra + denied
  → 管理员修改后提交
  → PATCH /common/auth/users/{username}/permissions
  → 后端重新计算 perms
  → 用户下次登录/刷新时拿到新权限
```


## 附录：后台接口速查

前端调用后台接口的统一前缀为 `/api/v1`，认证方式为 `Authorization: Bearer {JWT}`。

### 文件夹接口（`/case/folders`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/folders/tree` | xmind:view | 返回所有文件夹列表 |
| POST | `/folders` | xmind:manage | 新建文件夹 |
| PATCH | `/folders/{folder_id}` | xmind:manage | 重命名 |
| PATCH | `/folders/{folder_id}/parent` | xmind:manage | 移动文件夹 |
| DELETE | `/folders/{folder_id}` | xmind:manage | 级联删除 |

### 导图接口（`/case/maps`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/maps` | xmind:view | 按文件夹列/全库搜索 |
| POST | `/maps` | xmind:edit | 新建导图 |
| POST | `/maps/import` | xmind:edit | 批量导入 `.xmind` |
| GET | `/maps/{map_id}` | xmind:view | 详情：草稿 + 最新版本 |
| PATCH | `/maps/{map_id}` | xmind:edit | 草稿自动保存/重命名 |
| DELETE | `/maps/{map_id}` | xmind:delete | 软删除 |
| PATCH | `/maps/{map_id}/folder` | xmind:edit | 移动导图 |
| POST | `/maps/{map_id}/copy` | xmind:edit | 复制导图 |
| POST | `/maps/{map_id}/lock` | xmind:edit | 申请编辑锁 |
| DELETE | `/maps/{map_id}/lock` | xmind:edit | 释放编辑锁 |

### 版本接口（`/case/maps/{map_id}/...`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/maps/{map_id}/versions` | xmind:view | 版本历史 |
| GET | `/maps/{map_id}/versions/{version_no}` | xmind:view | 指定版本内容 |
| POST | `/maps/{map_id}/snapshot` | xmind:edit | 创建/覆盖版本快照 |
| POST | `/maps/{map_id}/rollback` | xmind:edit | 回滚到指定版本 |

### 资产接口（`/case/assets`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/assets/check_hash` | xmind:edit | 秒传检查 |
| POST | `/assets/upload` | xmind:edit | 上传图片 |
| DELETE | `/assets/{asset_id}` | xmind:delete | 删除资产 |

### 错误码速查

| HTTP | 场景 |
|------|------|
| 401 | 未登录 |
| 403 | 无权限/释放他人锁 |
| 404 | 资源不存在 |
| 400 | 文件夹超三层/移动到自身或子孙 |
| 423 | 导图已被他人锁定 |
| 502 | resourceplatform 上传/删除失败 |
