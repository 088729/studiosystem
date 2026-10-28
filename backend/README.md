# Studio System Backend

XMind 用例导图管理后端，基于 FastAPI + Beanie + MongoDB。

## 功能

- 用户认证与 RBAC+ACL 权限（JWT）
- 用例文件夹管理（最多三层）
- 思维导图编辑、版本快照、回滚
- 编辑锁（1 分钟超时 + 心跳续期）
- 可插拔文件存储（默认本地磁盘；内置 S3 兼容适配器，覆盖阿里云 OSS / 腾讯云 COS / 七牛 / 华为 OBS / MinIO / AWS S3 等；亦可对接自建 ResourcePlatform，见 `Design/Storage.md`）
- XMind 文件导入
- **Wiki 文档系统**：基于 Git 的在线 Obsidian
  - 每个文档库（Vault）一个 Git 仓库，文档即 `.md` 文件（GitPython 封装）
  - 文档 CRUD、目录树、保存三档（防抖保存不提交 / 手动全量提交 / 后台定时自动提交）
  - 编辑锁（10 分钟 TTL + 30s 心跳 + 409 返回持有者 + 窗口级令牌互斥；保存/加锁携带窗口 holder「用户名@windowId」，缺省退化为用户名兼容旧客户端，无令牌保存他人持锁页返回 409）
  - 版本历史、行级 diff、回滚（新提交不改写历史）
  - 全文搜索 / 反链 / 关系图谱（MongoDB 派生索引，`wiki_pages` + `wiki_links`，可重建）
  - 双链 `[[ ]]` 解析：悬空链接在目标页创建后自动转 resolved
  - 文档移动级联维护派生索引：目录移动批量改写 wiki_pages / wiki_links 路径前缀，单文档移动先落库改路径再重建索引并重指入链，不留幽灵节点
  - 附件作为普通文件进 Git 工作区 `attachments/`（上传 20MB 上限），随文档提交
  - Vault 生命周期状态机：`cloning / indexing / importing / ready / error`，远程克隆与本地导入（zip / 服务器目录）均后台异步执行，前端轮询 `status` 直至就绪
  - 权限四档：`wiki:view / edit / delete / manage`
  - 软删库 GC：软删 30 天后由后台循环每天物理清理磁盘目录 + Mongo 记录（自动提交循环内，无需人工干预）
  - pull/push 错误契约：拉取冲突返回 409 `wiki_pull_conflict`（附冲突文件列表）；推送被拒返回 409 `wiki_push_rejected`

## Wiki 接口一览

| 前缀 | 内容 |
|------|------|
| `/wiki/vaults` | 库列表 / 创建（空库或远程克隆）/ 详情 / 设置 / 删除（软删 30 天 + hard）/ pull / push / `import-zip` / `import-dir` |
| `/wiki/vaults/{vid}/pages` | 目录树 / 读写内容 / 新建 / 删除 / 移动 / commit / 编辑锁 |
| `/wiki/vaults/{vid}/history` | 提交历史 / diff / 回滚 |
| `/wiki/vaults/{vid}/explore` | 搜索 / 反链 / 图谱 / 任务式重建索引（202 语义） |
| `/wiki/vaults/{vid}/attachments` | 附件上传 / 按路径读取（媒体类型自动识别） |

## 启动

### 方式一：双击启动脚本（推荐本地开发）

```
studiosystem\backend\start.bat
```

### 方式二：命令行

```bash
# 1. 安装依赖
uv venv
uv pip install -e ".[dev]"

# 2. 环境变量已配置在 .env 中，按需修改

# 3. 启动（端口 8302，与前端代理一致）
.venv/Scripts/uvicorn app.main:app --reload --port 8302
```

## 测试

```bash
.venv/Scripts/pytest tests/ -v
```

Wiki 模块测试在 `tests/test_wiki.py`（5 个用例：全生命周期 / 冲突与幂等 / 附件 / zip 导入 / 目录导入与克隆状态机）；文件存储相关测试在 `tests/test_task_attachments.py` / `test_comment_upload.py` / `test_assets.py`（通过 mock 存储后端，不落盘、不依赖网络）。

## 文件存储

图片 / 附件默认存**本地磁盘**（`STORAGE_DIR`，默认 `./data/uploads`），经后端 `/uploads` 静态访问，零外部依赖；生产环境请把该目录挂载到持久化卷。三种后端按 `STORAGE_BACKEND` 切换，写入 `.env` 即可，业务功能完全一致。

### 配置示例

```bash
# ① local —— 本地磁盘（默认，推荐开源 / 单机部署）
STORAGE_BACKEND=local
STORAGE_DIR=./data/uploads

# ② s3 —— S3 兼容对象存储（阿里云 OSS 示例；COS / 七牛 / OBS / MinIO 换端点即可）
STORAGE_BACKEND=s3
STORAGE_S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
STORAGE_S3_ACCESS_KEY=你的AccessKey
STORAGE_S3_SECRET_KEY=你的SecretKey
STORAGE_S3_BUCKET=桶名
STORAGE_S3_REGION=cn-hangzhou
STORAGE_S3_ADDRESSING=virtual
STORAGE_S3_PUBLIC_BASE=https://桶名.oss-cn-hangzhou.aliyuncs.com

# ③ resourceplatform —— 自建文件服务（已有部署沿用）
STORAGE_BACKEND=resourceplatform
RESOURCEPLATFORM_BASE_URL=https://你的域名/resourceplatform
RESOURCEPLATFORM_TOKEN=你的令牌
```

各云端点预设（腾讯云 COS / 七牛 / 华为 OBS / MinIO / AWS）见 `.env.example`。桶需提前创建；直链模式建议桶设公共读，否则内嵌到评论等长生命周期内容的图片（预签名 7 天）会过期。切换后端不迁移存量文件——旧文件继续从原位置访问，新文件写入新后端。

自建部署可通过 `STORAGE_BACKEND=resourceplatform` 对接已有的 ResourcePlatform 文件服务（NAS 等）。设计细节与扩展指南（MinIO / S3 适配）见 `Design/Storage.md`。

### 手动验证存储链路

```bash
# local 后端（默认 8302 实例）：三条上传链路 + /uploads 访问校验，用后自动清理
.venv/Scripts/python.exe verify_storage.py

# s3 后端：先起本地 S3 模拟器（moto，dev 依赖已含），再起一个 s3 实例（8303）验证
.venv/Scripts/python.exe -m moto.server -p 9010 -H 127.0.0.1
# 新开终端（PowerShell）：
$env:STORAGE_BACKEND='s3'; $env:STORAGE_S3_ENDPOINT_URL='http://127.0.0.1:9010'
$env:STORAGE_S3_ACCESS_KEY='test'; $env:STORAGE_S3_SECRET_KEY='test'; $env:STORAGE_S3_BUCKET='studio-test'
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8303
# 再开一个终端跑验证（自动建桶，预签名 URL 访问校验）：
.venv/Scripts/python.exe verify_storage.py http://127.0.0.1:8303 --bucket studio-test
```

对接真实云（阿里云 OSS / 腾讯云 COS 等）时把 `STORAGE_S3_*` 换成对应端点与密钥即可，各云预设见 `.env.example`。

## 近期修复

- `GET /api/v1/case/maps/{map_id}` 在新建导图后偶发 500：修复 `map_service.get_map_detail` 中时区不一致的 datetime 比较，并增加 `latest_version.root` 的兜底检查。

## 默认账号

首次启动时会自动创建 `admin` 用户：

- 用户名：`admin`
- 密码：`admin123`（本地开发默认）
- 也可通过环境变量 `ADMIN_INITIAL_PASSWORD` 自定义密码
- 生产环境务必设置 `ADMIN_INITIAL_PASSWORD` 与 `SECRET_KEY`
