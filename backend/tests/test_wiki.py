"""Wiki 模块端到端测试：Vault 管理 / 文档 CRUD / 锁 / 提交 / 历史 / 搜索 / 反链 / 移动 / 删除。

使用独立测试库（conftest 已隔离），Git 仓库落在 backend/data/wiki（gitignore 已覆盖）。
"""
import asyncio

import pytest


async def _create_vault(client, token, name="测试库"):
    r = await client.post(
        "/api/v1/wiki/vaults",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "description": "ut"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_wiki_full_lifecycle(client, admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    vid = await _create_vault(client, admin_token)

    # 建两篇文档：先建目标 b.md，再建引用它的 docs/a.md
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                          json={"path": "b.md", "content": "target body\n"})
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                          json={"path": "docs/a.md", "content": "# A\n\nhello world [[b]] #tag1\n"})
    assert r.status_code == 200, r.text

    # 标题提取
    assert r.json()["title"] == "A"

    # 目录树：docs 文件夹 + b.md
    tree = (await client.get(f"/api/v1/wiki/vaults/{vid}/pages/tree", headers=h)).json()
    assert len(tree) == 2
    folder = next(n for n in tree if n["type"] == "folder")
    assert folder["name"] == "docs" and folder["children"][0]["path"] == "docs/a.md"

    # 反链：b.md 被 docs/a.md 引用
    bl = (await client.get(f"/api/v1/wiki/vaults/{vid}/explore/backlinks", headers=h,
                           params={"path": "b.md"})).json()
    assert [x["path"] for x in bl] == ["docs/a.md"]

    # 搜索：标题 / 正文 / 标签
    res = (await client.get(f"/api/v1/wiki/vaults/{vid}/explore/search", headers=h,
                            params={"q": "hello"})).json()
    assert any(x["path"] == "docs/a.md" and x["kind"] == "body" for x in res)
    res = (await client.get(f"/api/v1/wiki/vaults/{vid}/explore/search", headers=h,
                            params={"tag": "tag1"})).json()
    assert [x["path"] for x in res] == ["docs/a.md"]
    res = (await client.get(f"/api/v1/wiki/vaults/{vid}/explore/search", headers=h,
                            params={"q": "A"})).json()
    assert any(x["kind"] == "title" for x in res)

    # 非法路径 400
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                          json={"path": "../evil.md", "content": "x"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "wiki_path_invalid"

    # 编辑锁：加锁 / 重复加锁（自己）/ 释放
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages/lock", headers=h, json={"path": "docs/a.md"})
    assert r.status_code == 200
    r = await client.delete(f"/api/v1/wiki/vaults/{vid}/pages/lock", headers=h,
                            params={"path": "docs/a.md"})
    assert r.status_code == 200

    # 保存（自动保存，不 commit）→ 提交 → 历史/diff
    r = await client.put(f"/api/v1/wiki/vaults/{vid}/pages/content", headers=h,
                         json={"path": "docs/a.md", "content": "# A\n\nhello world v2\n"})
    assert r.status_code == 200, r.text

    # 未提交状态可见
    detail = (await client.get(f"/api/v1/wiki/vaults/{vid}", headers=h)).json()
    assert len(detail["changes"]) >= 1

    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages/commit", headers=h,
                          json={"message": "更新 a"})
    assert r.status_code == 200, r.text
    assert r.json()["committed"] is True
    commit1 = r.json()["commit"]

    history = (await client.get(f"/api/v1/wiki/vaults/{vid}/history", headers=h,
                                params={"path": "docs/a.md"})).json()
    msgs = [e["message"] for e in history]
    assert "更新 a" in msgs

    diff = (await client.get(f"/api/v1/wiki/vaults/{vid}/history/diff", headers=h,
                             params={"path": "docs/a.md", "commit": commit1})).json()
    assert "v2" in diff["diff"]

    # 再保存 v3 并提交，然后回滚到 commit1 → 内容应为 v2 而非 v3
    await client.put(f"/api/v1/wiki/vaults/{vid}/pages/content", headers=h,
                     json={"path": "docs/a.md", "content": "# A\n\nhello world v3\n"})
    await client.post(f"/api/v1/wiki/vaults/{vid}/pages/commit", headers=h, json={"message": "v3"})
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/history/revert", headers=h,
                          json={"path": "docs/a.md", "commit": commit1})
    assert r.status_code == 200, r.text
    content = (await client.get(f"/api/v1/wiki/vaults/{vid}/pages/content", headers=h,
                                params={"path": "docs/a.md"})).json()
    assert "v2" in content["content"] and "v3" not in content["content"]

    # 移动 b.md → docs/b.md，目录树跟随；更新 a.md 引用新路径后反链恢复
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages/move", headers=h,
                          json={"src": "b.md", "dst": "docs/b.md"})
    assert r.status_code == 200, r.text
    tree = (await client.get(f"/api/v1/wiki/vaults/{vid}/pages/tree", headers=h)).json()
    folder = next(n for n in tree if n["type"] == "folder")
    assert sorted(c["path"] for c in folder["children"]) == ["docs/a.md", "docs/b.md"]
    await client.put(f"/api/v1/wiki/vaults/{vid}/pages/content", headers=h,
                     json={"path": "docs/a.md", "content": "# A\n\nsee [[docs/b.md]]\n"})
    bl = (await client.get(f"/api/v1/wiki/vaults/{vid}/explore/backlinks", headers=h,
                           params={"path": "docs/b.md"})).json()
    assert [x["path"] for x in bl] == ["docs/a.md"]

    # 删除文档 + 删除库（hard）
    r = await client.delete(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                            params={"path": "docs/a.md"})
    assert r.status_code == 200
    r = await client.delete(f"/api/v1/wiki/vaults/{vid}", headers=h, params={"hard": "true"})
    assert r.status_code == 200
    r = await client.get(f"/api/v1/wiki/vaults/{vid}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_wiki_duplicate_and_conflict(client, admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    vid = await _create_vault(client, admin_token, "冲突库")

    # 重名库 409
    r = await client.post("/api/v1/wiki/vaults", headers=h, json={"name": "冲突库"})
    assert r.status_code == 409

    # 重复文档 409
    await client.post(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                      json={"path": "a.md", "content": "1"})
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages", headers=h,
                          json={"path": "a.md", "content": "2"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "wiki_page_exists"

    # 提交新建的文档 → 成功；再次提交无变更 → committed=false
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages/commit", headers=h, json={})
    assert r.json()["committed"] is True
    r = await client.post(f"/api/v1/wiki/vaults/{vid}/pages/commit", headers=h, json={})
    assert r.json()["committed"] is False


@pytest.mark.asyncio
async def test_wiki_attachments(client, admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    vid = await _create_vault(client, admin_token, "附件库")

    # 上传 PNG（1x1 像素）
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000d49444154789c626001000000ffff030000060005"
        "57bfabd40000000049454e44ae426082"
    )
    r = await client.post(
        f"/api/v1/wiki/vaults/{vid}/attachments",
        headers=h,
        files={"file": ("test.png", png, "image/png")},
    )
    assert r.status_code == 200, r.text
    att = r.json()
    assert att["path"] == "attachments/test.png"
    assert att["size"] == len(png)

    # 读取附件字节与媒体类型
    r = await client.get(f"/api/v1/wiki/vaults/{vid}/attachments/content",
                         headers=h, params={"path": "attachments/test.png"})
    assert r.status_code == 200
    assert r.content == png
    assert r.headers["content-type"].startswith("image/png")

    # 重名上传 → 自动加后缀
    r = await client.post(
        f"/api/v1/wiki/vaults/{vid}/attachments",
        headers=h,
        files={"file": ("test.png", png, "image/png")},
    )
    assert r.json()["path"] == "attachments/test-2.png"

    # 路径越界 → 400；不存在的附件 → 404
    r = await client.get(f"/api/v1/wiki/vaults/{vid}/attachments/content",
                         headers=h, params={"path": "a.md"})
    assert r.status_code == 400
    r = await client.get(f"/api/v1/wiki/vaults/{vid}/attachments/content",
                         headers=h, params={"path": "attachments/none.png"})
    assert r.status_code == 404

    # 超过 20MB → 400
    big = b"0" * (20 * 1024 * 1024 + 1)
    r = await client.post(
        f"/api/v1/wiki/vaults/{vid}/attachments",
        headers=h,
        files={"file": ("big.bin", big, "application/octet-stream")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "wiki_attachment_too_large"

    # 清理
    await client.delete(f"/api/v1/wiki/vaults/{vid}", headers=h, params={"hard": "true"})


@pytest.mark.asyncio
async def test_wiki_import_zip(client, admin_token):
    import io
    import zipfile

    h = {"Authorization": f"Bearer {admin_token}"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("笔记/第一页.md", "# 第一页\n\n来自 zip 导入\n")
        zf.writestr("attachments/pic.png", b"fakepng")
    buf.seek(0)

    r = await client.post(
        "/api/v1/wiki/vaults/import-zip",
        headers=h,
        files={"file": ("我的笔记.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    vault = r.json()
    vid = vault["id"]
    assert vault["status"] in ("importing", "indexing", "ready")

    # 轮询直至就绪（后台任务在同事件循环内执行）
    for _ in range(100):
        detail = (await client.get(f"/api/v1/wiki/vaults/{vid}", headers=h)).json()
        if detail["status"] in ("ready", "error"):
            break
        await asyncio.sleep(0.1)
    assert detail["status"] == "ready", detail.get("status_message")
    assert detail["doc_count"] == 1

    content = (await client.get(f"/api/v1/wiki/vaults/{vid}/pages/content", headers=h,
                                params={"path": "笔记/第一页.md"})).json()
    assert "来自 zip 导入" in content["content"]

    # 清理
    await client.delete(f"/api/v1/wiki/vaults/{vid}", headers=h, params={"hard": "true"})


@pytest.mark.asyncio
async def test_wiki_import_dir_and_clone(client, admin_token, tmp_path):
    import subprocess

    h = {"Authorization": f"Bearer {admin_token}"}

    # ---- 目录导入（无 .git，纯复制）----
    src = tmp_path / "本地笔记"
    src.mkdir()
    (src / "a.md").write_text("# A\n", encoding="utf-8")
    r = await client.post("/api/v1/wiki/vaults/import-dir", headers=h,
                          json={"path": str(src)})
    assert r.status_code == 200, r.text
    vid1 = r.json()["id"]
    for _ in range(100):
        d1 = (await client.get(f"/api/v1/wiki/vaults/{vid1}", headers=h)).json()
        if d1["status"] in ("ready", "error"):
            break
        await asyncio.sleep(0.1)
    assert d1["status"] == "ready", d1.get("status_message")
    assert d1["doc_count"] == 1

    # ---- 本地 git 仓库 → clone 导入（异步状态机）----
    remote = tmp_path / "remote-repo"
    remote.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=remote, check=True,
                   capture_output=True)
    (remote / "远程页.md").write_text("# 远程\n\nclone 来的\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-m", "init"], cwd=remote, check=True, capture_output=True)

    r = await client.post("/api/v1/wiki/vaults", headers=h,
                          json={"name": "克隆库", "remote_url": str(remote)})
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("cloning", "indexing", "ready")
    vid2 = r.json()["id"]

    for _ in range(100):
        d2 = (await client.get(f"/api/v1/wiki/vaults/{vid2}", headers=h)).json()
        if d2["status"] in ("ready", "error"):
            break
        await asyncio.sleep(0.1)
    assert d2["status"] == "ready", d2.get("status_message")
    assert d2["doc_count"] == 1
    content = (await client.get(f"/api/v1/wiki/vaults/{vid2}/pages/content", headers=h,
                                params={"path": "远程页.md"})).json()
    assert "clone 来的" in content["content"]

    # 克隆失败 → error 状态（不存在的远程）
    r = await client.post("/api/v1/wiki/vaults", headers=h,
                          json={"name": "坏克隆库", "remote_url": str(tmp_path / "no-such")})
    assert r.status_code == 200
    vid3 = r.json()["id"]
    for _ in range(100):
        d3 = (await client.get(f"/api/v1/wiki/vaults/{vid3}", headers=h)).json()
        if d3["status"] in ("ready", "error"):
            break
        await asyncio.sleep(0.1)
    assert d3["status"] == "error"
    assert d3["status_message"]

    # 清理
    await client.delete(f"/api/v1/wiki/vaults/{vid1}", headers=h, params={"hard": "true"})
    await client.delete(f"/api/v1/wiki/vaults/{vid2}", headers=h, params={"hard": "true"})
    await client.delete(f"/api/v1/wiki/vaults/{vid3}", headers=h, params={"hard": "true"})
