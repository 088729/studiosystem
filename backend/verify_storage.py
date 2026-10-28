"""存储后端手动验证脚本：对指定 BASE 的后端跑三条上传链路 + 访问校验。

用法：
  python verify_storage.py [BASE]            # BASE 默认 http://127.0.0.1:8302（local 后端）
  python verify_storage.py http://127.0.0.1:8303 --bucket studio-test
  # s3 后端（8303 实例需以 STORAGE_BACKEND=s3 启动）时用 --bucket 指定桶，脚本会自动建桶；
  # URL 语义为 7 天预签名（未配置公共域名时），脚本会带签名访问校验。

用后自动清理（测试任务 / 导图 / 对象与桶）。
"""
import base64
import sys

import boto3
import httpx

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else "http://127.0.0.1:8302"
    bucket = None
    if "--bucket" in sys.argv:
        bucket = sys.argv[sys.argv.index("--bucket") + 1]

    c = httpx.Client(base_url=base, timeout=20)
    r = c.post("/api/v1/common/auth/login", json={"username": "admin", "password": "admin123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    out = {}

    if bucket:
        # s3 模式：先建桶（moto/MinIO 均不会自动建）
        boto3.client(
            "s3",
            endpoint_url="http://127.0.0.1:9010",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        ).create_bucket(Bucket=bucket)
        out["bucket_created"] = bucket

    # 1) 任务附件
    r = c.post("/api/v1/task/tasks", headers=h, json={"title": "存储验证-附件"})
    task_id = r.json()["id"]
    r = c.post(f"/api/v1/task/tasks/{task_id}/attachments/upload", headers=h, files={"file": ("t.png", PNG, "image/png")})
    att = r.json()["attachments"][-1]
    out["attachment"] = {"path": att["resource_id"], "url": att["url"], "status": r.status_code}

    # 2) 评论图片
    r = c.post("/api/v1/task/comments/upload-image", headers=h, files={"file": ("c.png", PNG, "image/png")})
    out["comment_image"] = {**r.json(), "status": r.status_code}

    # 3) 导图资产
    r = c.post("/api/v1/case/maps", headers=h, json={"title": "存储验证-导图"})
    map_id = r.json()["id"]
    r = c.post("/api/v1/case/assets/upload", headers=h, data={"map_id": map_id, "node_id": "n1"}, files={"file": ("m.png", PNG, "image/png")})
    asset = r.json()
    out["case_asset"] = {"url": asset.get("url"), "relative_path": asset.get("relative_path"), "status": r.status_code}

    # 4) 访问校验（本地=同源 /uploads；s3=预签名 URL 直接 GET）
    for key, item in out.items():
        if not isinstance(item, dict) or "url" not in item:
            continue
        url = item["url"]
        if url.startswith("http"):
            g = httpx.get(url, timeout=20)
        else:
            g = c.get(url)
        item["static_get"] = g.status_code
        item["is_png"] = g.content[:4] == b"\x89PNG"

    # 清理
    c.delete(f"/api/v1/task/tasks/{task_id}", headers=h)
    c.delete(f"/api/v1/case/maps/{map_id}", headers=h)
    out["cleaned"] = True

    print(out)
    ok = all(v.get("static_get") == 200 and v.get("is_png") for k, v in out.items() if isinstance(v, dict) and "static_get" in v)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
