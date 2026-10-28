# Wiki 模块设计文档（后台篇）

> 覆盖：需求 · 数据库设计 · 后台设计 · 接口设计 · 权限
> 范围限定：基于 Git 的文档仓库（类 Obsidian 知识库）。文档本体存 Git 仓库，MongoDB 仅存索引与元数据。

---

## 一、需求背景与目标

### 1.1 业务背景

团队需要统一的在线知识库沉淀测试文档、设计文档、会议记录、学习笔记等。现有方案（本地 Obsidian / 语雀 / 飞书文档）存在：版本不可控、无法离线、与个人仓库割裂、历史回溯困难等问题。本模块将 Obsidian 的核心体验在线化，并用 Git 作为底层存储，让文档天然具备版本历史、可克隆、可同步远程的能力。

### 1.2 核心目标

| 目标 | 说明 |
|------|------|
| Git 文档仓库 | 每个文档库（Vault）即一个 Git 仓库，文档即 `.md` 文件，可 clone/pull/push 到远程 |
| 多库管理 | 支持创建多个 Vault（如：测试文档库、团队知识库、个人笔记库），互不干扰 |
| 在线编辑 | 类 Obsidian 的所见即所得 Markdown 编辑（Vditor），支持双链语法、代码块、数学公式 |
| 版本管理 | 自动保存 + 自动/手动提交，历史即 `git log`，支持版本对比（diff）与回滚 |
| 双链与图谱 | `[[wiki-link]]` 解析、反向链接面板、全局关系图谱 |
| 全文搜索 | 按标题/正文/标签搜索，标题与正文分权重 |
| 权限分级 | 查看 / 编辑 / 删除 / 管理四档权限 |
| 协作互斥 | 编辑锁防止多人同时改同一篇文档 |

### 1.3 模块边界

- **本模块负责**：Vault 管理、文档 CRUD、Git 提交与历史、双链索引、搜索、图谱数据、编辑锁。
- **不在本模块**：多人实时协同编辑（OT/CRDT）、文档评论批注、发布为公开站点（静态站点导出可后续追加）、AI 问答（可后续基于索引扩展）。

---

## 二、总体架构

### 2.1 技术选型

| 层 | 技术 | 说明 |
|----|------|------|
| Git 操作 | GitPython | 服务端 Git 仓库的增删改查、commit、diff、分支、远程同步 |
| 后端 | FastAPI + Beanie（MongoDB ODM） | 与现有模块一致 |
| 文档索引 | MongoDB（4 个集合） | Vault 注册表、文档索引、链接关系 |
| Markdown 解析 | 正则 + markdown-it-py（可选） | 提取双链、嵌入、标签、frontmatter |
| 前端 | Vue 3 + Element Plus + Vditor | Vditor 提供 WYSIWYG / 即时渲染 / 分屏三模式 |
| 图谱渲染 | ECharts (graph) | 前端渲染节点关系图 |
| 文件存储 | 服务端本地磁盘（Vault 工作目录） | 文档本体与 Git 对象均在磁盘；附件走 resourceplatform |

### 2.2 核心设计原则：Git 为事实源（Source of Truth）

```
┌──────────────────────────────────────────────────────┐
│  前端编辑器                                          │
│    读文档 ◄──────────┐                               │
│    自动保存 ──────────┤                               │
│    手动提交 ──────────┤  HTTP /api/v1/wiki/...        │
└───────────────────────┼───────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│  后端 Wiki 服务                                      │
│  ┌─────────────┐   ┌──────────────┐  ┌────────────┐ │
│  │ 索引服务     │   │ Vault 注册表  │  │ 权限/锁     │ │
│  │ wiki_pages  │◄─►│ wiki_vaults  │  │ 服务        │ │
│  │ wiki_links  │   └──────┬───────┘  └────────────┘ │
│  └─────────────┘          │                         │
│                           ▼                         │
│                  ┌─────────────────┐                 │
│                  │ GitPython 封装   │                 │
│                  │ services/wiki/  │                 │
│                  └────────┬────────┘                 │
└───────────────────────────┼──────────────────────────┘
                            ▼
              ┌─────────────────────────┐
              │ 磁盘：每个 Vault 一个    │
              │ Git 仓库（工作区+.git） │
              └─────────────────────────┘
```

- **文档内容**：只存在 Git 仓库的工作区文件中，MongoDB **不存正文**（与 XMind 模块的 `case_versions` 存全文不同）。
- **MongoDB 索引**：从 Git 文件系统派生（denormalized），用于列表、搜索、反链、图谱。允许重建，损坏后可通过「重建索引」任务恢复。
- **版本历史**：直接读 `git log`，不单独建集合。

### 2.3 后端代码结构

```
app/
├── models/wiki/
│   ├── __init__.py
│   ├── wiki_vault.py               # WikiVault   → wiki_vaults
│   ├── wiki_page.py                # WikiPage    → wiki_pages（索引，非正文）
│   └── wiki_link.py                # WikiLink    → wiki_links（双链关系）
├── services/wiki/
│   ├── __init__.py
│   ├── git_repo.py                 # GitPython 封装：init/clone/commit/diff/revert/mv/pull/push
│   ├── vault_service.py            # Vault 生命周期 + 路径安全
│   ├── page_service.py             # 文档读写、路径规范化、标题提取
│   ├── index_service.py            # 索引同步：单篇 upsert / 全量重建
│   ├── link_parser.py              # 解析 [[wiki-link]]、![[embed]]、#tag、frontmatter
│   └── search_service.py           # 标题/正文/标签搜索、反链、图谱数据组装
├── api/v1/endpoints/wiki/
│   ├── __init__.py
│   ├── vaults.py                   # Vault 管理 + 远程同步
│   ├── pages.py                    # 文档 CRUD / 移动 / 提交
│   ├── history.py                  # 版本历史 / diff / 回滚
│   └── explore.py                  # 搜索 / 反链 / 图谱 / 重建索引
└── core/config.py                  # 新增 wiki 配置段
```

路由注册（`app/api/v1/router.py` 追加）：

```python
from app.api.v1.endpoints.wiki import vaults as wiki_vaults, pages as wiki_pages
from app.api.v1.endpoints.wiki import history as wiki_history, explore as wiki_explore

api_router.include_router(wiki_vaults.router,  prefix="/wiki/vaults",   tags=["文档库"])
api_router.include_router(wiki_pages.router,   prefix="/wiki/vaults",   tags=["文档-页面"])
api_router.include_router(wiki_history.router, prefix="/wiki/vaults",   tags=["文档-历史"])
api_router.include_router(wiki_explore.router, prefix="/wiki/vaults",   tags=["文档-探索"])
```

### 2.4 Git 仓库目录与配置

**放置位置**：每个 Vault 一个**工作区仓库**（非裸仓库），集中放在可配置根目录下：

```
# 开发（后端工作目录 ./data/wiki，已加入 .gitignore）
studiosystem/backend/data/wiki/
└── {vault_repo_dir}/          # repo_dir = uuid，由后端生成，与库名解耦防路径注入
    ├── .git/
    ├── .gitattributes         # init 时生成
    ├── .gitignore             # init 时生成（临时文件 + .obsidian/）
    └── ...(md 目录与附件)

# 生产（K3s：hostPath / PVC 挂载到容器 /data/wiki）
/data/wiki/{vault_repo_dir}/
```

- 根目录由配置项 `wiki_repo_root` 指定（默认 `./data/wiki`），`config.py` 新增：
  ```python
  wiki_repo_root: str = "./data/wiki"      # 生产通过环境变量 WIKI_REPO_ROOT 指向挂载卷
  wiki_git_author_email_suffix: str = "wiki.local"
  ```
- 部署：K3s `deployment.yaml` 需为后端容器挂载 hostPath/PVC 到 `WIKI_REPO_ROOT`（当前后端为无状态单副本，不加卷 Pod 重建即丢文档，属必配项）。
- **不做本地裸仓**：备份与分发靠 push 远程，不在服务端另存 bare。

**初始化配置**（`git init -b main` 后立即写入，GitPython 通过 `repo.config_writer()`）：

| 配置 | 值 | 原因 |
|------|----|----|
| `core.quotepath` | `false` | 中文路径不以 `\344\270...` 转义显示 |
| `core.autocrlf` | `false` | 统一靠 `.gitattributes`，避免 Windows 提交时全库 CRLF 噪音 diff |
| `core.longpaths` | `true` | Windows 长路径（>260 字符） |
| `gc.auto` | `256` | 自动提交频繁，默认 6700 太宽松，`.git` 对象会快速膨胀 |
| `user.name` / `user.email` | **不设** | 提交身份每次由 GitPython `Actor(name, email)` 传入（用户提交用 `username`，系统提交用 `wikibot`），避免多人共用同一仓库身份 |

**`.gitattributes`（init 生成）**——不加这行，Windows 开发机上 `autocrlf=true` 会导致每次保存全文件 diff：

```
* text=auto eol=lf
*.md text eol=lf
attachments/** -text
```

**`.gitignore`（init 生成）**——兼容本地 Obsidian 打开同一仓库的场景：

```
~$*
*.tmp
.obsidian/workspace*    # 本地 Obsidian 工作区状态，不入库
.trash/                 # Obsidian 本地回收目录
```

**`safe.directory`（容器部署必配）**：K3s 挂载卷属主与容器运行用户不一致时，git 2.35+ 会拒绝操作（`detected dubious ownership`）。镜像启动脚本或 lifespan 初始化中执行：

```python
import subprocess
subprocess.run(
    ["git", "config", "--system", "--add", "safe.directory", wiki_repo_root],
    check=True,
)
```

（system 级配置落在容器内，不污染宿主；开发机直跑无此问题。）

### 2.5 数据集合总览

```
wiki_vaults    ← Vault 注册表（名称、磁盘路径、远程地址、可见性）
wiki_pages     ← 文档索引（路径、标题、标签、最近提交时间，不含正文）
wiki_links     ← 链接关系（源路径 → 目标路径，含未解析链接）
```

关系：

```
WikiVault (1) ──< WikiPage (N) ──< WikiLink (N, 指向其它 WikiPage 或悬空)
```

---

## 三、数据库设计

### 3.1 WikiVault（`wiki_vaults`）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 库名，项目内唯一（用户可见） |
| description | str | 描述，可空 |
| owner | str | 创建者 username |
| repo_dir | str | 服务端磁盘目录名（uuid，不直接用库名，防路径注入） |
| remote_url | Optional[str] | 远程仓库地址（https/ssh），可空 |
| default_branch | str | 默认分支，默认 `main` |
| visibility | str | `internal`（登录用户可见，默认）/ `private`（仅 owner 与 `wiki:manage`）；一期实现 internal，字段预留 |
| auto_commit_interval | int | 自动提交间隔（秒），默认 300，0 表示关闭 |
| is_deleted | bool | 软删除标记 |
| created_at / updated_at | datetime | 时间戳 |

索引：`name` 唯一（过滤 is_deleted）、`owner`。

> 注：`repo_dir` 存相对目录名，真实路径由配置 `WIKI_REPO_ROOT` + `repo_dir` 拼接，接口层永不直接接收磁盘路径。

### 3.2 WikiPage（`wiki_pages`）

每篇 `.md` 文档一行索引。正文不落库。

| 字段 | 类型 | 说明 |
|------|------|------|
| vault_id | Indexed(str) | 所属 Vault |
| path | str | 仓库内相对路径（`docs/a/b.md`，POSIX 风格，统一 `/`） |
| title | str | 标题：优先 frontmatter `title`，其次首个 H1，再次文件名 |
| folder | str | 所在目录（`docs/a`），根为 `""` |
| tags | List[str] | 合并 frontmatter tags + 正文 `#tag`（去重） |
| size | int | 字节数 |
| last_commit_at | Optional[datetime] | 最近提交时间（列表排序/展示用；历史定位一律走 `git log --follow -- path`，不依赖存储的 commit 指针） |
| created_at / updated_at | datetime | 取自 Git 提交时间（索引用） |
| locked_by / locked_at | Optional | 编辑锁，语义同 XMind 模块 |

索引：`(vault_id, path)` 唯一、`(vault_id, folder)`、`(vault_id, tags)`。

### 3.3 WikiLink（`wiki_links`）

保存文档时由 `link_parser` 全量替换该文档的链接记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| vault_id | str | 所属 Vault |
| src_path | str | 源文档路径 |
| dst_path | Optional[str] | 归一化后的目标文档路径；悬空链接为 `null` |
| dst_alias | str | 链接原文（如 `[[笔记|别名]]` 的 `笔记|别名`） |
| link_type | str | `wiki`（`[[]]`）/ `embed`（`![[]]`）/ `md`（标准 `[](x.md)`） |
| is_resolved | bool | 目标是否存在 |

索引：`(vault_id, src_path)`、`(vault_id, dst_path)`、`(vault_id, is_resolved)`（图谱/反链查询）。

### 3.4 路径与命名规范

- 路径一律 POSIX 风格（`/` 分隔），接口出入参、MongoDB 存储均为该形式；写盘时转平台路径。
- 仅允许扩展名 `.md` 作为文档；目录通过路径中的 `/` 表达，不单独建模。
- 非法路径直接 400：`..`、绝对路径、`\`、控制字符、保留名（`.git`、`CON`、`NUL` 等）。
- 重命名/移动走 `git mv`，保留历史。

---

## 四、Markdown 解析规范（`link_parser.py`）

保存或重建索引时解析：

| 元素 | 语法 | 处理 |
|------|------|------|
| Wiki 链接 | `[[目标]]` / `[[目标|别名]]` / `[[目标#标题]]` | 目标按「路径去扩展名 → 同库全文路径」解析，记录 `link_type=wiki`，`#标题` 锚点截断后再匹配路径 |
| 嵌入 | `![[目标]]` | 同上，`link_type=embed`，前端渲染为内容预览块 |
| 标准链接 | `[文本](相对路径.md)` | 相对当前文档目录归一化，`link_type=md`；外链（http://、//）忽略 |
| 标签 | `#tag`（行内，非代码块） | `[a-zA-Z0-9_\-/\u4e00-\u9fa5]`；代码块/行内代码内的 `#` 不提取 |
| Frontmatter | 文件头 `---` YAML | 提取 `title`、`tags`、`aliases`、`created`；YAML 解析失败不阻断保存，仅记 warn |

目标解析规则（同 Obsidian）：先在 Vault 内按「去扩展名的相对路径」精确匹配；否则按「任意目录下同名（去扩展名）」匹配；仍失败则 `is_resolved=false` 保留原文。

---

## 五、后台设计

### 5.1 鉴权与权限

沿用平台权限键，新增：

```python
PermissionKeyItem(key="wiki:view",   builtin=True),
PermissionKeyItem(key="wiki:edit",   builtin=True),
PermissionKeyItem(key="wiki:delete", builtin=True),
PermissionKeyItem(key="wiki:manage", builtin=True),   # 建库/删库/远程同步/重建索引
```

- `wiki:view`：读文档、搜索、图谱、历史。
- `wiki:edit`：新建/保存/移动/提交/回滚、加锁。
- `wiki:delete`：删除文档与目录。
- `wiki:manage`：创建/删除 Vault、配置远程、pull/push、全库重建索引。
- 所有接口走 `deps.py` 现有 `require_permission` 依赖；锁与归属校验在 service 层。

### 5.2 Git 操作封装（`services/wiki/git_repo.py`）

对 GitPython 的统一封装，屏蔽异常为业务错误：

| 方法 | 说明 |
|------|------|
| `init_vault(dir, branch)` | `git init -b main` → 写入 2.4 节 `.gitattributes` / `.gitignore` → 写入 core 配置（quotepath/autocrlf/longpaths/gc.auto）→ 空提交 `init: vault` |
| `clone_vault(url, dir)` | 克隆远程；失败回滚目录 |
| `read_file(dir, path)` / `write_file(dir, path, content)` | 工作区读写（含父目录创建） |
| `list_tree(dir)` | 递归列出 `.md` 文件（`git ls-files` + 工作区状态合并） |
| `commit(dir, message, author_name, author_email)` | 仅当有变更时提交；无变更返回 `None` |
| `log_file(dir, path, limit)` | 单文件历史（`git log --follow -- path`） |
| `diff_commit(dir, commit_a, commit_b, path)` | 文本 diff（unified），限制最大行数 |
| `revert_file(dir, path, commit)` | 检出历史版本为新提交（`git checkout <commit> -- path` + commit），不改写历史 |
| `move_file(dir, src, dst)` | `git mv`（目标存在则 409） |
| `remove_file(dir, path)` | 删除并提交 |
| `pull(dir)` / `push(dir, token)` | 远程同步；凭证用配置/库级 token，不落日志 |
| `status(dir)` | 工作区变更列表（用于「未提交变更」提示） |

**提交身份**：以当前登录用户作为 author（`username <username@wiki.local>`），系统提交（自动提交）用 `wikibot <wikibot@wiki.local>`。Git 用户名仅用于历史展示，与平台账号解耦。

### 5.3 保存与提交策略

三档写路径，兼顾体验与历史整洁：

| 操作 | 接口 | 行为 |
|------|------|------|
| 自动保存（编辑器防抖） | `PUT /pages/content` | 写工作区文件 + 更新 `wiki_pages` 索引（标题/标签/链接）；**不 commit**。页面在「未提交变更」中可见 |
| 手动提交 | `POST /pages/commit` | 对该 Vault 当前所有变更 commit，message 可自定义（默认 `update: <path>`） |
| 定时自动提交 | 后台 asyncio 任务 | 每 Vault 按 `auto_commit_interval` 扫描，有变更则 `auto: snapshot N files` 提交 |

回滚、diff、历史均基于已提交版本；未提交内容可通过前端「未提交变更」面板对比。

后台任务在 `main.py` lifespan 中启停（与 `asset_gc` 同模式）：

```python
from app.services.wiki.auto_commit import start_auto_commit, stop_auto_commit
# lifespan 内 start_auto_commit() / stop_auto_commit()
```

`stop_auto_commit()` 为优雅停机：**先对所有 dirty Vault 补一次提交**（`shutdown: flush pending changes`），再取消任务——避免「自动保存已写工作区但未到定时提交点」的内容停留在历史之外，被运维误当垃圾清理。

### 5.4 索引同步（`index_service.py`）

- **单篇 upsert**：`PUT /pages/content`、`POST /pages`、`DELETE`、revert、move 后同步执行——解析 frontmatter/标签/链接，替换该 `src_path` 的 `wiki_links`，更新 `wiki_pages`。
- **全量重建**：`POST /explore/rebuild-index`（`wiki:manage`）——清空两集合后遍历 `git ls-files` 重建；用于 clone 后初始化、索引损坏恢复。实现为后台任务，返回 `task_id` 供轮询。
- **克隆后初始化**：`POST /vaults` 带 `remote_url` 时，clone 完成即触发该 Vault 的重建。

### 5.5 编辑锁（`POST /pages/lock`、`DELETE /pages/lock`）

语义与 XMind 模块一致：锁存于 `wiki_pages.locked_by/locked_at`，默认 10 分钟过期（可续期）。保存时校验：
- 无锁 → 直接保存并上锁（前端进入编辑即加锁）；
- 有锁且属于自己 → 正常保存；
- 有锁属于他人且未过期 → 409 + 锁持有者信息；
- 过期锁 → 抢占并提示。

文档关闭/切换时前端调 `DELETE` 释放。与 XMind 不同的是：因 Git 兜底，即便锁失效产生并发写，也以「后写覆盖 + 双版本提示」降级处理，不丢已提交历史。

### 5.6 搜索 / 反链 / 图谱（`explore.py` + `search_service.py`）

- **搜索** `GET /explore/search?q=&tag=`：MongoDB 正则查询（忽略大小写），标题命中排前、正文命中其次；数据量大（>10 万篇）时可平滑切换 `text` 索引，接口契约不变。返回路径、标题、命中片段（截取 ±40 字符）。
- **反链** `GET /explore/backlinks?path=`：查 `wiki_links.dst_path = path and is_resolved`，聚合出引用方列表（标题 + 锚文本）。
- **图谱** `GET /explore/graph`：一次返回 `{nodes: [{path,title,tags}], edges: [{src,dst,type}]}`，仅 `is_resolved=true`；前端 ECharts 渲染。大库限制返回前 N（默认 500）个高度数节点。

### 5.7 附件

一期文档内图片通过 Vditor 上传（走 `/case/assets` 同款 resourceplatform 服务，或 `WikiAsset` 独立集合），正文插入 `![name](attach://asset_id)` 或相对路径附件目录 `attachments/`。推荐后者：附件作为普通文件进 Git 工作区（如 `attachments/xxx.png`），随文档一起提交，Obsidian 习惯一致且远程同步时一并带走。体积上限沿用资源平台策略（单文件 20MB）。

### 5.8 错误处理约定

GitPython 异常统一映射：

| 场景 | HTTP |
|------|------|
| 路径非法/越界 | 400 |
| 文档/Vault 不存在 | 404 |
| 目标已存在（新建/移动冲突） | 409 |
| 被他人锁定 | 409 + `lock_holder` |
| 远程同步失败（网络/凭证） | 502 |
| 索引重建中 | 202（任务式） |

统一错误体沿用 `{"detail": {"code": "wiki_xxx", "message": "..."}}`。

---

## 六、接口设计

### 6.1 Vault（`/wiki/vaults`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/wiki/vaults` | Vault 列表（名称/描述/远程/文档数/未提交数） | wiki:view |
| POST | `/wiki/vaults` | 创建。body：`{name, description?, remote_url?, auto_commit_interval?}`；带 remote 则 clone 并初始化索引 | wiki:manage |
| GET | `/wiki/vaults/{vid}` | 详情 + `status` 未提交变更列表 | wiki:view |
| PATCH | `/wiki/vaults/{vid}` | 改名/描述/远程/自动提交间隔 | wiki:manage |
| DELETE | `/wiki/vaults/{vid}` | 软删除（默认保留磁盘 30 天）/ `?hard=true` 连同目录删除 | wiki:manage |
| POST | `/wiki/vaults/{vid}/pull` | git pull，完成后增量重建索引 | wiki:manage |
| POST | `/wiki/vaults/{vid}/push` | git push（库级 token 或全局配置） | wiki:manage |

### 6.2 文档页面（`/wiki/vaults/{vid}/pages`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/wiki/vaults/{vid}/pages/tree` | 目录树：`[{path, title, folder, children?}]`（来自 `wiki_pages` 索引聚合） | wiki:view |
| GET | `/wiki/vaults/{vid}/pages/content?path=` | 读正文 + 元信息 + 锁状态 | wiki:view |
| POST | `/wiki/vaults/{vid}/pages` | 新建 `{path, content}`；冲突 409 | wiki:edit |
| PUT | `/wiki/vaults/{vid}/pages/content` | 保存正文（自动保存，不 commit） | wiki:edit |
| DELETE | `/wiki/vaults/{vid}/pages` | 删除 `?path=`（递归删目录需 `?recursive=true`） | wiki:delete |
| POST | `/wiki/vaults/{vid}/pages/move` | `{src, dst}`，`git mv` | wiki:edit |
| POST | `/wiki/vaults/{vid}/pages/commit` | `{message?}` 提交全部变更，返回 commit 信息 | wiki:edit |
| POST | `/wiki/vaults/{vid}/pages/lock` / `DELETE` | 加锁/释放（body/query 带 path） | wiki:edit |

### 6.3 历史（`/wiki/vaults/{vid}/history`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/wiki/vaults/{vid}/history?path=&limit=` | 单文件提交历史（含作者、时间、message） |
| GET | `/wiki/vaults/{vid}/history/diff?path=&commit=&compare=` | 与上一版本或指定版本 diff，返回 unified diff 文本 |
| POST | `/wiki/vaults/{vid}/history/revert` | `{path, commit}` 检出旧版本为新提交 |

### 6.4 探索（`/wiki/vaults/{vid}/explore`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/wiki/vaults/{vid}/explore/search?q=&tag=` | 全文搜索 |
| GET | `/wiki/vaults/{vid}/explore/backlinks?path=` | 反链列表 |
| GET | `/wiki/vaults/{vid}/explore/graph` | 图谱节点边 |
| POST | `/wiki/vaults/{vid}/explore/rebuild-index` | 全量重建索引（任务式） |

### 6.5 错误码约定

`wiki_path_invalid` / `wiki_vault_not_found` / `wiki_page_not_found` / `wiki_page_exists` / `wiki_locked` / `wiki_remote_error` / `wiki_rebuild_running`。

---

## 七、关键流程时序

### 7.1 打开并编辑文档

```
前端                后端                  Git                 MongoDB
 │  GET content      │                    │                     │
 │──────────────────>│ read_file + 锁状态  │                     │
 │                   │───────────────────>│                     │
 │  进入编辑          │                    │                     │
 │  POST lock ──────>│ upsert wiki_pages.locked_by              │
 │  (防抖) PUT content│                    │                     │
 │──────────────────>│ write_file ───────>│ 写工作区             │
 │                   │ index_service: 更新 title/tags/links      │
 │  关闭/切换 DELETE lock ───────────────>│ 释放锁               │
```

### 7.2 提交与回滚

```
提交：POST pages/commit → git add -A + commit(author=user) → 更新 wiki_pages.head_commit
回滚：POST history/revert {path,commit}
      → git checkout <commit> -- path
      → git commit("revert: <path> to <short>")
      → index_service 单篇重建
```

---

## 八、注意事项

1. **并发**：同一 Vault 的写操作（写文件/commit/mv）在 service 层按 `vault_id` 加 asyncio 锁，串行化；GitPython 对象非线程安全，禁止跨协程复用 `Repo` 实例，每次操作 `Repo(path)` 现取。
2. **磁盘配额**：每 Vault 在 `PATCH` 与 auto commit 时统计工作区大小，超阈值（默认 2GB）拒绝写入并报错，防 `.git` 膨胀。
3. **远程凭证**：`remote_url` 中的 token 仅存服务端（可加密落库），日志与接口回显一律脱敏；push 优先使用库级 token，其次全局 deploy key。
4. **`.gitignore`**：Vault 初始化时写入（临时文件、系统垃圾），避免脏工作区。
5. **定时任务幂等**：auto commit 任务崩溃恢复后按「有无变更」判断，不产生空提交；进程重启扫描所有 Vault 恢复调度。
6. **软删除**：Vault 删除先软删（列表不可见），保留磁盘便于恢复；30 天后由 GC 任务物理清理（与 XMind `asset_gc` 同机制，可加进同一循环）。
7. **大文件**：单文档 >1MB 拒绝保存（编辑器应拆分）；`git diff` 输出限 5000 行，超出截断并标记。
8. **中文路径**：Git 默认对非 ASCII 路径 quoted，GitPython 读取时设置 `core.quotepath=false`，接口层统一 UTF-8。
9. **pull 冲突策略**：`pull` 前若工作区有未提交变更，先自动提交（`sync: auto commit before pull`）再 `git pull --rebase`；rebase 产生冲突时立即 `git rebase --abort`，保持本地原状，返回 409 + 冲突文件列表，由用户在界面上选择「保留本地/保留远程/手动整理」。**永不自动解决冲突**。
10. **push 被拒**：non-fast-forward 时自动「pull --rebase → 再 push」重试一次；仍失败返回 409，提示先执行 pull。
11. **per-vault 锁管理**：asyncio 锁存于模块级 `dict[vault_id, Lock]`（惰性创建），Vault 删除时清理，防止泄漏。
12. **兼容本地 Obsidian**：`.obsidian/`（工作区状态）与 `.trash/` 已在 init 时写入 `.gitignore`，用户可将同一仓库 clone 到本地用 Obsidian 编辑，pull 后互不影响。

---

## 九、分期实施建议

| 期 | 内容 | 验收 |
|----|------|------|
| 一期 | Vault 管理（新建/列表/删除）、文档树、CRUD、Vditor 编辑、锁、手动+自动 commit、历史/diff/回滚、基础搜索 | 完整文档闭环 + 版本可追溯 |
| 二期 | 双链解析与反链面板、关系图谱、标签体系、frontmatter、附件入 Git | 类 Obsidian 核心体验 |
| 三期 | 远程 clone/pull/push、导入本地 vault（zip/目录）、模板、每日笔记、出站链接检查（悬空链接报告） | 远程同步与存量迁移 |
