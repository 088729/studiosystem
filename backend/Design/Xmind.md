# XMind 模块设计文档（后台篇）

> 覆盖：需求 · 数据库设计 · 后台设计 · 接口设计 · 权限
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

### 2.2 后端代码结构

```
app/
├── models/case/
│   ├── case_folder.py              # CaseFolder  → case_folders
│   ├── case_map.py                 # CaseMap     → case_maps
│   ├── case_version.py             # CaseVersion → case_versions
│   └── case_asset.py               # CaseAsset   → case_assets
└── api/v1/endpoints/case/
    ├── folders.py                  # 文件夹接口
    ├── maps.py                     # 导图接口
    └── assets.py                   # 图片资产接口
```

路由注册：

```python
api_router.include_router(folders.router,     prefix="/case/folders", tags=["用例-文件夹"])
api_router.include_router(maps.router,        prefix="/case/maps",    tags=["用例-导图"])
api_router.include_router(case_assets.router, prefix="/case/assets",  tags=["用例-资产"])
```

### 2.3 数据集合总览

```
case_folders    ← 文件夹层级（最多三层 depth 0/1/2）
case_maps       ← 导图元数据（身份、锁、草稿指针、当前版本号）
case_versions   ← 导图内容快照（完整节点树，全量历史）
case_assets     ← 图片等二进制资产元数据（文件本体在 SMB）
```

关系：

```
CaseFolder (1) ──< CaseMap (N) ──< CaseVersion (N, 按 version_no 自增)
                           └──< CaseAsset (N)
```

---

## 三、数据库设计

### 3.1 CaseFolder（`case_folders`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `name` | str | 文件夹名 |
| `parent_id` | str / null | 父文件夹 ID；null = 根（depth 0） |
| `depth` | int | 0/1/2，后端写入时强制校验，超出拒绝 |
| `owner` | str | 创建者用户名 |
| `created_at` | datetime | 创建时间（UTC） |

索引：`parent_id` 升序。

**层级约束**：创建时取父文件夹 `depth + 1`，超过 2 返回 400；前端在 `depth ≥ 2` 时隐藏"新建文件夹"入口（双重拦截）。

**删除策略**：级联递归——BFS 收集所有子孙文件夹 ID，软删除其下所有 `case_maps`，再物理删除文件夹本身。

### 3.2 CaseMap（`case_maps`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键，对外即 `map_id` |
| `title` | str | 导图标题 |
| `owner` | str | 创建者用户名 |
| `folder_id` | str / null | 所属文件夹；null = 根目录 |
| `is_deleted` | bool | 软删除标记，GC 定期物理清理 |
| `current_version` | int | 当前最新版本号（新建为 1） |
| `temp_content` | Any / null | 实时草稿，不计版本号 |
| `locked_by` | str / null | 当前锁定人 username；null = 未锁定 |
| `locked_at` | datetime / null | 锁定最后活跃时间，超时自动失效 |
| `created_at` | datetime | 创建时间（UTC） |

索引：`folder_id` 升序、`is_deleted` 升序。

### 3.3 CaseVersion（`case_versions`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `map_id` | str | 关联 CaseMap 的 `str(_id)` |
| `version_no` | int | 版本序号，从 1 自增 |
| `root` | Any | simple-mind-map 完整节点树（含 layout/theme/view） |
| `changelog` | str | 版本说明，默认 "系统自动保存" |
| `operator_id` | str | 操作人用户名 |
| `created_at` | datetime | 创建时间（UTC） |

索引：`(map_id, version_no)` 升序**唯一复合索引**。

**版本触发来源**：

| 来源 | changelog |
|------|-----------|
| 新建导图 | "初始版本" |
| 用户手动保存，填写说明 | 用户填写内容 |
| 前端自动快照（末级节点数达 5 的倍数） | "系统自动保存" |
| 版本回滚 | "回滚至 v{N}" |
| 复制导图 | "复制自 {源标题}" |
| 导入 .xmind | "xmind 导入" |

**回滚实现**：将目标版本的 `root` 原样写入新的 CaseVersion（version_no 自增），不覆盖已有版本，保留完整历史。

### 3.4 CaseAsset（`case_assets`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键，对外即 `asset_id` |
| `map_id` | str | 所属导图 `str(_id)` |
| `node_id` | str | 关联的节点 UID |
| `url` | str | 文件完整访问 URL（绝对路径） |
| `file_type` | str | MIME 类型，如 `image/png` |
| `file_size` | int | 字节数 |
| `file_hash` | str | **MD5**，用于秒传去重 |
| `relative_path` | str | 资源相对路径，用于删除 |
| `refer_count` | int | 引用计数，默认 1 |
| `is_orphan` | bool | 引用归零时标记为孤儿，默认 false |
| `created_at` | datetime | 创建时间（UTC） |

索引：`map_id`、`file_hash`、`is_orphan` 各升序。

**图片存储路径**：`case/{map_id}/{file_hash}.{ext}`，通过 resourceplatform `POST /api/upload` 写入 SMB。

**图片访问 URL**：`{PUBLIC_BASE_URL}/{relative_path}`。例如 `https://your-domain.example.com/resourceplatform/case/{map_id}/{file_hash}.png`。上传后 resourceplatform 会返回完整 `url`，XMind 后端直接保存到 `CaseAsset.url`。

**GC 策略**：后台定期扫描 `is_orphan=True` 的记录，二次确认 URL 不出现在任何版本 root 字符串中后，调用 resourceplatform `DELETE /api/files/{relative_path}` 物理删除文件，再删 DB 记录。

---

## 四、用例节点结构规范

> **已变更**：节点类型（`node_type`）功能已删除，连带移除快照结构校验（422 `invalid_leaf_nodes`）和 `case_count` 用例数统计。节点数据只保留 `text`/`uid`/`expand` 等通用字段；存量数据中的 `node_type`/`tag` 字段为无害残留，无需迁移。

---

## 五、后台设计

### 5.1 鉴权与权限

所有接口通过 `OAuth2PasswordBearer` 从请求头取 JWT，调用 `get_current_user(token)` 解析用户。`_require_perm(token, perm)` 统一校验：

- 无 token → 401
- 用户 `perms` 列表含 `"*"`（管理员）→ 放行所有
- 否则要求指定 perm 在列表中，否则 403

四个权限 key：

| Key | 说明 |
|-----|------|
| `xmind:view` | 查看导图、浏览文件夹 |
| `xmind:edit` | 新建/编辑导图、上传图片、申请锁 |
| `xmind:delete` | 删除导图、删除资产 |
| `xmind:manage` | 管理文件夹（增删改移） |

### 5.2 草稿自动保存（`PATCH /maps/{map_id}`）

- 前端 `data_change` 事件防抖 2s 后调用
- 请求体 `{ temp_content, title? }`，写入 `temp_content`，**不涨版本号**
- 用 `BackgroundTasks` 异步写入 MongoDB，接口立即返回 `{"message": "更新中"}`
- 同时刷新 `locked_at`（若当前用户即锁定人），保持编辑锁活跃

### 5.3 版本快照（`POST /maps/{map_id}/snapshot`）

请求体关键字段：`root`、`changelog`、`overwrite`。

流程：

1. `overwrite=true`：覆盖当前版本的 root/changelog/operator/created_at，清空 temp_content
2. `overwrite=false`（默认）：version_no 自增，新建 CaseVersion，清空 temp_content

### 5.4 编辑锁（`POST/DELETE /maps/{map_id}/lock`）

实际超时为 **1 分钟**（`LOCK_TIMEOUT_MINUTES = 1`），配合前端心跳续期。

| 时机 | 操作 |
|------|------|
| 打开编辑器 | `POST /lock`：写 `locked_by` + `locked_at`；若已被他人锁定且未超时 → 423（含 `locked_by`） |
| 草稿自动保存 | 刷新 `locked_at`，等价心跳续期 |
| 关闭编辑器 / 保存版本 | `DELETE /lock`：仅锁定人或管理员可释放，否则 403 |
| 页面意外关闭 | 前端 `beforeunload` 尽力发送释放请求（不保证） |
| 超 1 分钟无操作 | 后端在下次 lock 请求时检查 `locked_at`，超时视为自动释放 |

### 5.5 XMind 文件导入（`POST /maps/import`）

支持一次上传多个 `.xmind` 文件，每个文件创建一张导图 + 一个初始版本。

- `.xmind` 本质是 zip，优先读 `content.json`（XMind 8+），回退 `content.xml`（旧版）
- 递归将 XMind topic 转为 simple-mind-map 节点格式 `{ data: { text }, children: [] }`
- 每个文件独立 try/except，单文件失败不影响其他，返回 `results` 列表含 `map_id`/`title`/`version_no` 或 `error`

### 5.6 复制导图（`POST /maps/{map_id}/copy`）

- 只复制最新版本内容作为初始版本，不复制历史
- 同文件夹内标题重名时自动加 `(1)`、`(2)` 后缀
- 默认复制到同文件夹，可指定 `folder_id`

### 5.7 图片资产（`assets.py`）

- `check_hash`：按 `map_id` + `file_hash` + `is_orphan=False` 查询，存在则返回 URL（秒传）
- `upload`：读文件 → 算 MD5 → 秒传检查 → 调 resourceplatform `POST /api/upload` 写 SMB（路径 `case/{map_id}/{hash}.{ext}`，请求头带 `X-Token`）→ 写 CaseAsset 记录；秒传命中则 `refer_count += 1`
- `delete`：调 resourceplatform `DELETE /api/files/{relative_path}`（请求头带 `X-Token`，404 视为已删）→ 删 DB 记录

### 5.8 列表查询（`GET /maps`）

- 有 `q` 参数：全库按标题模糊搜索（正则转义、大小写不敏感），按 `created_at` 倒序，限 50 条
- 无 `q`：按 `folder_id` 过滤（留空 = 根目录），返回所有未软删导图

---

## 六、接口设计

所有接口前缀 `/api/v1`，认证方式 Bearer Token（JWT）。

### 6.1 文件夹（`/case/folders`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/folders/tree` | xmind:view | 返回所有文件夹列表（前端自行组装树） |
| POST | `/folders` | xmind:manage | 新建文件夹（body: `name`, `parent_id?`），超三层返回 400 |
| PATCH | `/folders/{folder_id}` | xmind:manage | 重命名（body: `name`） |
| PATCH | `/folders/{folder_id}/parent` | xmind:manage | 移动（body: `parent_id?`），BFS 更新子孙 depth，防循环 |
| DELETE | `/folders/{folder_id}` | xmind:manage | 级联递归删除：软删其下导图 + 物理删文件夹 |

**GET `/folders/tree` 响应**：

```json
{
  "items": [
    { "id": "...", "name": "战斗模块", "parent_id": null, "depth": 0, "owner": "zhangsan", "created_at": "..." }
  ]
}
```

### 6.2 导图（`/case/maps`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/maps` | xmind:view | `?folder_id=` 按文件夹列；`?q=` 全库模糊搜（互斥） |
| POST | `/maps` | xmind:edit | 新建（body: `title`, `folder_id?`, `root?`），含初始版本 |
| POST | `/maps/import` | xmind:edit | 批量导入 `.xmind`（multipart `files`, `folder_id?`） |
| GET | `/maps/{map_id}` | xmind:view | 详情：草稿 + 最新版本 root + 锁状态 |
| PATCH | `/maps/{map_id}` | xmind:edit | 草稿自动保存（异步）/ 重命名，刷新锁活跃 |
| DELETE | `/maps/{map_id}` | xmind:delete | 软删除 |
| PATCH | `/maps/{map_id}/folder` | xmind:edit | 移动到文件夹（body: `folder_id?`） |
| POST | `/maps/{map_id}/copy` | xmind:edit | 复制（body: `folder_id?`） |
| POST | `/maps/{map_id}/lock` | xmind:edit | 申请锁，被占返回 423 |
| DELETE | `/maps/{map_id}/lock` | xmind:edit | 释放锁 |

**GET `/maps/{map_id}` 响应**：

```json
{
  "id": "...",
  "title": "关卡测试",
  "owner": "zhangsan",
  "folder_id": "...",
  "current_version": 3,
  "created_at": "2026-04-01T10:00:00",
  "last_modified_at": "2026-04-14T15:30:00",
  "temp_content": null,
  "latest_root": { "root": {...}, "layout": "logicalStructure", "theme": {...}, "view": {...} },
  "locked_by": null,
  "locked_at": null
}
```

### 6.3 版本（`/case/maps/{map_id}/...`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/maps/{map_id}/versions` | xmind:view | 分页版本历史（`?offset=&limit=`，仅元数据） |
| GET | `/maps/{map_id}/versions/{version_no}` | xmind:view | 指定版本完整 root |
| POST | `/maps/{map_id}/snapshot` | xmind:edit | 创建/覆盖版本快照 |
| POST | `/maps/{map_id}/rollback` | xmind:edit | 回滚到指定版本（body: `version_no`，新建快照） |

**POST `/snapshot` 请求体**：

```json
{
  "root": { "root": {...}, "layout": "...", "theme": {...}, "view": {...} },
  "changelog": "补充异常路径用例",
  "overwrite": false
}
```

### 6.4 资产（`/case/assets`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/assets/check_hash` | xmind:edit | 秒传检查（body: `map_id`, `file_hash`） |
| POST | `/assets/upload` | xmind:edit | 上传图片（multipart `map_id`, `node_id`, `file`） |
| DELETE | `/assets/{asset_id}` | xmind:delete | 物理删除（SMB + DB） |

### 6.5 错误码约定

| HTTP | 场景 |
|------|------|
| 401 | 未登录（无 token） |
| 403 | 无权限 / 释放他人锁 |
| 404 | 文件夹/导图/版本/资产不存在 |
| 400 | 文件夹超三层 / 移动到自身或子孙 |
| 423 | 导图已被他人锁定 |
| 502 | resourceplatform 上传/删除失败 |

---

## 八、关键流程时序

### 8.1 编辑保存流程

```
用户打开导图
  → POST /maps/{id}/lock              # 申请锁（被占→423→只读）
  → GET  /maps/{id}                   # 取草稿+最新版本
  → [草稿存在?] → 弹框恢复/放弃
  → 初始化 MindMap

用户编辑（每次改动）
  → 防抖 2s
  → PATCH /maps/{id}  temp_content    # 异步存草稿 + 续锁

用户点"保存版本"
  → POST /maps/{id}/snapshot          # 200 → 清空草稿

用户关闭编辑器
  → DELETE /maps/{id}/lock            # 释放锁
```

### 8.2 版本回滚流程

```
用户在版本历史选 v2 → 点回滚
  → POST /maps/{id}/rollback  { version_no: 2 }
  → 后端取 v2 的 root，写入新版本 v{N+1}（changelog="回滚至 v2"）
  → 清空 temp_content
  → 前端重新加载最新版本
```

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

## 十一、用户与权限模块

> 平台级基础设施，为 XMind 模块提供登录认证、RBAC+ACL 权限、用户管理。

### 11.1 总体设计

- **认证**：账号密码登录，签发 JWT（HS256），`perms` 写入 JWT claims
- **授权模型**：RBAC（角色）+ ACL（个人 extra/denied）双层；`denied` 优先级最高；`*` 超级通配
- **权限计算**：`perms = (角色基础权限 ∪ extra_permissions) − denied_permissions`；若角色或 extra 含 `*`，直接返回 `["*"]`

### 11.2 数据模型

#### 集合总览

```
users                    ← 本地用户及权限配置
roles                    ← 角色与基础权限
sso_platform_config      ← 单文档：所有内置/自定义权限 key
```

#### User（`users` 集合）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `username` | str (unique) | 用户名，唯一索引 |
| `role_name` | str | 本平台角色名，默认 `viewer` |
| `extra_permissions` | List[str] | 个人追加权限 |
| `denied_permissions` | List[str] | 个人禁止权限（优先级最高） |
| `full_name` | str | 姓名 |
| `email` | str | 邮箱 |
| `department` | str | 部门 |
| `job_scope` | str | 工作职能 |
| `is_active` | bool | 在职状态 |
| `last_login_at` | datetime / null | 最后登录时间 |
| `created_at` | datetime | 创建时间（UTC） |
| `updated_at` | datetime | 更新时间（UTC） |

索引：
- `username` 升序唯一索引
- `role_name` 升序（方便按角色批量查询）
- `is_active` 升序

#### Role（`roles` 集合）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `name` | str (unique) | 角色标识，唯一索引 |
| `permissions` | List[str] | 基础权限 key，`["*"]` 全权限 |
| `description` | str / null | 描述 |
| `is_builtin` | bool | 是否内置，内置不可删除 |
| `created_at` | datetime | 创建时间（UTC） |

内置角色（启动时幂等写入）：

| 角色 | 权限 | 说明 |
|------|------|------|
| `admin` | `["*"]` | 超级管理员 |
| `tester` | `["xmind:view", "xmind:edit", "xmind:delete", "task:view", "task:create", "task:run"]` | 测试人员 |
| `developer` | `["xmind:view", "task:view", "level:view", "log:view"]` | 开发人员 |
| `viewer` | `["xmind:view", "task:view", "level:view"]` | 只读用户 |

> 本项目当前仅聚焦 XMind，实际内置权限以代码为准。

#### PermissionKey / SsoPlatformConfig（`sso_platform_config` 单文档）

```json
{
  "permission_keys": [
    { "key": "xmind:view", "app_id": null, "builtin": true },
    { "key": "xmind:edit", "app_id": null, "builtin": true },
    { "key": "xmind:delete", "app_id": null, "builtin": true },
    { "key": "xmind:manage", "app_id": null, "builtin": true },
    { "key": "sys:manage", "app_id": null, "builtin": true }
  ]
}
```

启动时若单文档不存在则初始化；存在则补齐缺失内置 key，不覆盖自定义 key。

### 11.3 服务层

- `auth.create_access_token`：签发 JWT，remember_me=False→2h，True→30d
- `auth.get_current_user`：解析 JWT，返回用户 payload
- `auth.require_perm`：校验指定权限
- `permission.compute_permissions`：按 RBAC+ACL 计算最终权限列表
- `permission.sync_user`：登录时同步本地用户记录

### 11.4 接口设计

前缀 `/api/v1/common`。

#### 认证（`/auth`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/auth/login` | 公开 | Body `{username,password,remember_me?}` |
| GET | `/auth/me` | 登录 | 返回当前用户信息 |
| GET | `/auth/user/{username}` | 登录 | 查询用户 |
| POST | `/auth/verify` | 公开 | Body `{token}`；验证 JWT |

#### 用户管理（`/auth/users`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/auth/users` | sys:manage | 所有本地用户 |
| PATCH | `/auth/users/{username}/permissions` | sys:manage | Body `{role_name,extra,denied}` 全量替换 |
| POST | `/auth/users/batch-permissions` | sys:manage | 批量应用同一套权限 |
| PATCH | `/auth/users/{username}/active` | sys:manage | Body `{is_active}` |
| PATCH | `/auth/users/{username}/job-scope` | 本人或 sys:manage | Body `{job_scope}` |
| DELETE | `/auth/users/{username}` | sys:manage | 删本地记录 |

#### 角色与权限 Key（`/auth` + `/platform`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/auth/permissions` | 登录 | 权限 key 列表 |
| GET | `/auth/roles` | sys:manage | 角色列表 |
| POST | `/auth/roles` | sys:manage | 新建角色 |
| PATCH | `/auth/roles/{name}` | sys:manage | 全量替换角色权限 |
| DELETE | `/auth/roles/{name}` | sys:manage | 删除角色（内置拒绝） |
| GET | `/platform/permissions` | 登录 | 完整 key 对象 |
| POST | `/platform/permissions` | sys:manage | 新建权限 key |
| DELETE | `/platform/permissions/{key:path}` | sys:manage | 删除权限 key（内置拒绝） |

### 11.5 与 XMind 模块的关系

- `xmind:view/edit/delete/manage` 四个权限 key 由本模块启动时写入 SsoPlatformConfig
- XMind 所有接口经 `_require_perm(token, perm)` 校验（token 来自本模块 JWT）
- 导图的 `owner`/`locked_by`、版本的 `operator_id` 均取自 JWT `sub`
