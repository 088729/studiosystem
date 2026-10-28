"""S3 兼容存储后端单测：mock boto3 资源对象，不联网。

覆盖：上传（key 生成 / ContentType / url 拼接）、公共域名与预签名两种 URL 语义、删除。
"""
import pytest

from app.services.storage.s3 import S3Storage


class FakeObject:
    """boto3 Object 的替身：记录 put/delete 参数。"""

    def __init__(self, bucket, key, calls):
        self.bucket, self.key, self.calls = bucket, key, calls

    def put(self, Body=None, ContentType=None):
        self.calls.append({"key": self.key, "size": len(Body or b""), "content_type": ContentType})
        return {}

    def delete(self):
        self.calls.append({"deleted": self.key})
        return {}


class FakeS3Resource:
    def __init__(self, calls):
        self._calls = calls
        self.meta = type("Meta", (), {"client": type("Client", (), {
            "generate_presigned_url": staticmethod(
                lambda op, Params=None, ExpiresIn=None: f"https://presigned/{Params['Key']}"
            )
        })()})()

    def Object(self, bucket, key):
        return FakeObject(bucket, key, self._calls)


@pytest.fixture
def make_storage(monkeypatch):
    """构造注入 FakeS3Resource 的 S3Storage；settings 由 monkeypatch 覆盖。"""

    def _make(public_base=""):
        calls = []
        monkeypatch.setattr(
            "app.services.storage.s3.get_settings",
            lambda: type(
                "S",
                (),
                {
                    "storage_s3_bucket": "studio",
                    "storage_s3_public_base": public_base,
                    "storage_s3_endpoint_url": "https://oss-cn-hangzhou.aliyuncs.com",
                    "storage_s3_access_key": "ak",
                    "storage_s3_secret_key": "sk",
                    "storage_s3_region": "cn-hangzhou",
                    "storage_s3_addressing": "virtual",
                },
            )(),
        )
        monkeypatch.setattr(
            "app.services.storage.s3.boto3",
            type("B", (), {"resource": staticmethod(lambda *a, **k: FakeS3Resource(calls))})(),
        )
        return S3Storage(), calls

    return _make


@pytest.mark.asyncio
async def test_s3_upload_with_public_base(make_storage):
    storage, calls = make_storage(public_base="https://cdn.example.com")
    out = await storage.upload(b"data", "case/map1/abc.png", "case/map1")
    assert out == {
        "path": "case/map1/abc.png",
        "url": "https://cdn.example.com/case/map1/abc.png",
    }
    assert calls == [{"key": "case/map1/abc.png", "size": 4, "content_type": "image/png"}]


@pytest.mark.asyncio
async def test_s3_upload_presigned_fallback(make_storage):
    storage, _ = make_storage(public_base="")
    out = await storage.upload(b"data", "task/comments/xyz.png", "task/comments")
    assert out["url"] == "https://presigned/task/comments/xyz.png"


@pytest.mark.asyncio
async def test_s3_filename_sanitized(make_storage):
    storage, calls = make_storage(public_base="https://cdn.example.com")
    out = await storage.upload(b"x", r"..\weird name?.png", "task/comments")
    assert "/" not in out["path"].split("task/comments/")[-1]
    assert out["path"].endswith(".png")
    assert calls[0]["content_type"] == "image/png"


@pytest.mark.asyncio
async def test_s3_delete(make_storage):
    storage, _ = make_storage()
    out = await storage.delete("case/map1/abc.png")
    assert out == {"deleted": "case/map1/abc.png", "exists": False}
