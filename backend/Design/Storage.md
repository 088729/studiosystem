# 文件存储模块设计文档

> 覆盖：背景 · 架构 · 配置 · 数据模型 · 接口与静态访问 · 兼容性 · 扩展指南
> 范围限定：任务附件 / 任务评论图片 / 用例导图图片资产的文件本体存储。Wiki 附件不经过本模块（纯 Git 工作区文件）。

---

## 一、背景与目标

### 1.1 背景

系统最初的文件存储硬依赖外部 ResourcePlatform 文件服务（自建 NAS 部署）。开源场景下不应强迫使用者部署该服务，需要开箱即用的默认存储。

### 1.2 目标

| 目标 | 说明 |
|------|------|
| 零依赖默认 | 默认本地磁盘存储，`STORAGE_DIR` 目录 + `/uploads` 静态访问，无需任何外部服务 |
| 可插拔后端 | 统一 `StorageBackend` 接口，环境变量切换后端；自建 ResourcePlatform 部署继续可用 |
| 数据不迁移 | 切换后端不影响存量数据：旧绝对 URL 继续有效，新写入按所选后端存储 |
| 接口不变 | 业务层（4 个调用点）不感知后端差异，`upload/delete` 返回结构与原 RP 客户端一致 |

### 1.3 模块边界

- **本模块负责**：文件落盘 / 转发上传、删除、公开访问 URL 生成、文件名安全处理。
- **不在本模块**：业务校验（类型 / 大小白名单仍在各业务服务层）、下载鉴权（对齐原 RP 公开 GET 语义）、任务附件的物理 GC（仅导图资产有 GC）。

---

## 二、总体架构

```
业务层（不感知后端）
├─ task_service.upload_attachment      任务附件   task/{task_id}/{file}
├─ comment_service.upload_comment_image 评论图片  task/comments/{uuid}{ext}
├─ asset_service.upload_asset          导图资产   case/{map_id}/{md5}{ext}   （MD5 去重）
└─ asset_gc.run_asset_gc               资产 GC   delete(relative_path)
        │
        ▼  get_storage()  ← STORAGE_BACKEND 单例
┌─────────────────────────────────────────────┐
│ StorageBackend 接口                          │
│   upload(bytes, filename, path) -> {path,url}│
│   delete(relative_path) -> dict              │
├──────────────────┬──────────────────────────┤
│ LocalStorage     │ ResourcePlatformStorage   │
│ 落 STORAGE_DIR   │ 包装原 httpx 客户端       │
│ url=/uploads/... │ url=RP 绝对地址           │
└──────────────────┴──────────────────────────┘
```

### 2.1 LocalStorage（默认）

- 文件写入 `{STORAGE_DIR}/{path}/{filename}`，目录自动创建；
- 文件名服务端清洗：仅保留 `[A-Za-z0-9._-]`、去路径成分、限长 120、空名 uuid 兜底；重名追加 8 位 uuid 前缀防覆盖；
- 路径解析做目录穿越防护（resolve 后必须仍在根目录内）；
- 返回 `url = /uploads/{相对路径}`（**相对路径，域名无关**），由后端 `app.mount("/uploads", StaticFiles)` 公开访问；
- 删除幂等：文件不存在返回 `{"exists": False}` 不报错。

### 2.2 ResourcePlatformStorage

包装原 `ResourcePlatformClient`（`app/services/resource_platform.py` 原样保留），multipart 转发至 RP `/api/upload`，写操作带 `X-Token`；GET 为 RP 静态地址（无鉴权，语义与本地 `/uploads` 一致）。

### 2.3 静态访问路由

`main.py` 在 `STORAGE_BACKEND=local` 时挂载 `/uploads`。两条部署链路均已预配转发：

- 本地开发：`vite.config.js` 代理 `/uploads` → 8302；
- 容器/K8s：`frontend/nginx.conf` 反代 `/uploads/` → 后端（Ingress 场景亦需相应转发）。

---

## 三、配置

| 变量 | 默认 | 说明 |
|------|------|------|
| `STORAGE_BACKEND` | `local` | `local` \| `resourceplatform` |
| `STORAGE_DIR` | `./data/uploads` | local 后端根目录；**生产必须挂持久化卷（PVC/宿主目录）** |
| `RESOURCEPLATFORM_BASE_URL` | `http://localhost:9000` | 仅 resourceplatform 后端生效 |
| `RESOURCEPLATFORM_TOKEN` | 空 | 同上 |

切换后端只需改环境变量重启；两个后端可服务**同一份数据库**（旧记录的绝对 URL 指向 RP 继续可访问，新记录按新后端写入）。

### 3.1 配置示例

```bash
# ① local —— 本地磁盘（默认）
STORAGE_BACKEND=local
STORAGE_DIR=./data/uploads

# ② s3 —— 阿里云 OSS（其余云换端点，预设见 .env.example）
STORAGE_BACKEND=s3
STORAGE_S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
STORAGE_S3_ACCESS_KEY=...
STORAGE_S3_SECRET_KEY=...
STORAGE_S3_BUCKET=桶名
STORAGE_S3_REGION=cn-hangzhou
STORAGE_S3_ADDRESSING=virtual
STORAGE_S3_PUBLIC_BASE=https://桶名.oss-cn-hangzhou.aliyuncs.com

# ③ resourceplatform —— 自建文件服务
STORAGE_BACKEND=resourceplatform
RESOURCEPLATFORM_BASE_URL=http://localhost:9000
RESOURCEPLATFORM_TOKEN=change-me
```

桶需提前创建（local 后端的目录自动创建）；直链模式建议桶设公共读，否则预签名 URL（7 天）内嵌到评论等长生命周期内容会过期。

---

## 四、数据模型与 URL 语义

| 业务 | 引用字段 | url 形态 |
|------|----------|----------|
| 任务附件 `Task.attachments[]` | `resource_id` = 相对路径；`url` 冗余存储 | local: `/uploads/task/{id}/{file}`；RP: `http://rp-host/task/{id}/{file}` |
| 评论图片 | 无独立字段，URL 内嵌 `content` markdown | 同上（`task/comments/...`） |
| 导图资产 `CaseAsset` | `url` + `relative_path` + `file_hash`（MD5 去重） | 同上（`case/{map_id}/{md5}{ext}`） |

导图节点 `data.image / data.imgMap` 存储的即资产 `url`；资产 GC 以「带引号的 url 精确子串匹配全部版本 root JSON」判定引用，**URL 稳定性是 GC 正确性的前提**——因此 url 一经写入不再改写，切后端不迁移。

前端读取顺序：记录内 `url` 字段优先，缺失时按 `/uploads/{resource_id}` 兜底（本地后端语义）。

---

## 五、兼容性与迁移

- **不做数据迁移**：自建部署设 `STORAGE_BACKEND=resourceplatform` 行为与历史完全一致；新部署从零全为本地文件。
- **前后端混用**：理论上允许中途切换（旧文件留在原后端、新文件走新后端），但导图资产去重按 `(map_id, file_hash)` 命中旧记录会返回旧 URL——属预期（同一张图引用已存在的资产）。
- 若确需迁移存量文件：拷贝 RP 目录树至 `STORAGE_DIR` 并重写数据库中的 url 字段即可（相对路径替换），可作为后续运维脚本。

---

## 六、S3 兼容后端（常用云）

`STORAGE_BACKEND=s3` 启用 `LocalStorage` 之外的通用 S3 兼容适配器（`storage/s3.py`，boto3 线程池封装）。
一套适配器覆盖所有 S3 兼容云，**无需为每个云单独写类**：

| 云 | `STORAGE_S3_ENDPOINT_URL` | 寻址风格 |
|----|---------------------------|----------|
| AWS S3 | 留空（默认官方端点） | auto |
| 阿里云 OSS | `https://oss-cn-hangzhou.aliyuncs.com`（按地域） | virtual |
| 腾讯云 COS | `https://cos.ap-shanghai.myqcloud.com` | virtual |
| 七牛 Kodo | `https://s3.cn-east-1.qiniucs.com` | virtual |
| 华为云 OBS | `https://obs.cn-north-4.myhuaweicloud.com` | virtual |
| MinIO（NAS 自建） | `http://your-nas:9000` | path |
| Cloudflare R2 | `https://<account>.r2.cloudflarestorage.com` | path |

其余变量：`STORAGE_S3_ACCESS_KEY / SECRET_KEY / BUCKET / REGION`、`STORAGE_S3_ADDRESSING`（auto|path|virtual）、
`STORAGE_S3_PUBLIC_BASE`（桶的公共域名 / CDN 域名）。

**URL 语义**：配置 `PUBLIC_BASE` 时返回永久直链（推荐公共读桶，评论内嵌图片等长生命周期场景必须）；
留空时返回 7 天预签名 URL（私有桶可用，但内嵌长周期内容会过期）。key 生成复用共享的 `safe_filename`
（文件名清洗规则与本地后端一致）；同名覆盖（S3 put 语义），与原 RP 行为一致。

**依赖**：`pip install -e ".[s3]"`（boto3 可选扩展，未安装时仅在选中 s3 后端时才报错）。

**测试**：`tests/test_storage_s3.py`，mock boto3 资源对象，覆盖上传 key 生成 / ContentType / 两种 URL 语义 / 文件名清洗 / 删除。

### 6.1 扩展指南（新增非 S3 协议的后端）

1. 新建 `app/services/storage/<name>.py`，实现 `upload(file_bytes, filename, path) -> {"path", "url"}` 与 `delete(relative_path)`；
2. `storage/__init__.py::get_storage()` 增加分支；
3. 若访问需要签名 / 鉴权，前端优先使用后端返回的完整 `url`，签名 URL 天然兼容；仅 `resource_id` 兜底路径需相应调整。

业务层 4 个调用点与测试 mock 均面向 `get_storage()`，无需改动。

---

## 七、测试

| 文件 | 覆盖 |
|------|------|
| `tests/test_task_attachments.py` | 任务附件上传 / 登记 / 移除 / 非图片 400 / 任务不存在 404 |
| `tests/test_comment_upload.py` | 评论图片上传 / 类型与大小校验 / 未登录 401 |
| `tests/test_assets.py` | 导图资产上传 / MD5 去重（check_hash）/ 删除引用 |

测试通过 `patch("app.services.storage.get_storage")` 注入 mock（返回 `{path, url}` 结构与真实后端一致），不落盘、不依赖网络。
