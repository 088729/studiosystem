import shutil
from pathlib import Path
from typing import List, Optional

from git import Actor, Repo
from git.exc import GitCommandError

MAX_DIFF_LINES = 5000

GITATTRIBUTES = """* text=auto eol=lf
*.md text eol=lf
attachments/** -text
"""

GITIGNORE = """~$*
*.tmp
.obsidian/workspace*
.trash/
"""

BOT_NAME = "wikibot"


class WikiGitError(Exception):
    """Git 操作失败，message 面向调用方。"""

    def __init__(self, message: str, conflict_files: Optional[List[str]] = None):
        super().__init__(message)
        self.conflict_files = conflict_files or []


def _actor(name: str, email_suffix: str) -> Actor:
    return Actor(name, f"{name}@{email_suffix}")


def _open(root: Path) -> Repo:
    return Repo(str(root))


def init_vault(
    root: Path,
    branch: str = "main",
    email_suffix: str = "wiki.local",
    allow_nonempty: bool = False,
) -> None:
    """git init -b main + 写入 .gitattributes/.gitignore + core 配置 + 空提交。

    allow_nonempty=True 用于导入场景：目录已有内容，init 后跳过空提交，
    由调用方随后用实际内容做首个提交。
    """
    if root.exists() and not allow_nonempty:
        raise WikiGitError(f"目录已存在: {root}")
    repo = Repo.init(str(root), mkdir=True, initial_branch=branch)
    (root / ".gitattributes").write_text(GITATTRIBUTES, encoding="utf-8")
    (root / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    with repo.config_writer() as cfg:
        cfg.set_value("core", "quotepath", "false")   # 中文路径不转义
        cfg.set_value("core", "autocrlf", "false")    # 行尾统一靠 .gitattributes
        cfg.set_value("core", "longpaths", "true")    # Windows 长路径
        cfg.set_value("gc", "auto", "256")            # 自动提交频繁，控制 .git 膨胀
    if allow_nonempty:
        return
    actor = _actor(BOT_NAME, email_suffix)
    repo.index.add([".gitattributes", ".gitignore"])
    repo.index.commit("init: vault", author=actor, committer=actor)


def clone_vault(url: str, root: Path) -> None:
    try:
        repo = Repo.clone_from(url, str(root))
        # 对齐 init_vault 的核心配置（克隆来的仓库 quotepath 可能为 true，
        # 会导致中文路径被八进制转义、ls-files 解析丢文件）
        with repo.config_writer() as cfg:
            cfg.set_value("core", "quotepath", "false")
            cfg.set_value("core", "autocrlf", "false")
            cfg.set_value("core", "longpaths", "true")
            cfg.set_value("gc", "auto", "256")
    except Exception:
        # 失败回滚目录，避免留下半成品
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        raise


def read_file(root: Path, rel_path: str) -> str:
    return (root / rel_path).read_text(encoding="utf-8")


def write_file(root: Path, rel_path: str, content: str) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="")


def list_md_files(root: Path) -> List[str]:
    """git ls-files + 未跟踪文件，仅 .md，POSIX 相对路径。"""
    repo = _open(root)
    tracked = repo.git.ls_files().splitlines()
    files = set(p for p in tracked if p.endswith(".md"))
    files.update(p.replace("\\", "/") for p in repo.untracked_files if p.endswith(".md"))
    return sorted(files)


def has_changes(root: Path) -> bool:
    repo = _open(root)
    repo.git.add("-A")
    return bool(repo.index.diff("HEAD"))


def changed_files(root: Path) -> List[str]:
    """工作区相对 HEAD 的变更路径（含未跟踪），POSIX 风格。"""
    repo = _open(root)
    out = repo.git.status("--porcelain")
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip().strip('"').replace("\\", "/"))
    return files


def commit(
    root: Path,
    message: str,
    author_name: str,
    email_suffix: str = "wiki.local",
) -> Optional[str]:
    """有变更才提交，返回 commit hexsha；无变更返回 None。兼容仓库首个提交（无 HEAD）。"""
    repo = _open(root)
    repo.git.add("-A")
    try:
        repo.head.commit
        has_head = True
    except Exception:
        has_head = False
    if has_head and not repo.index.diff("HEAD"):
        return None
    actor = _actor(author_name, email_suffix)
    c = repo.index.commit(message, author=actor, committer=actor)
    return c.hexsha


def commit_detail(root: Path, hexsha: str) -> dict:
    """返回提交的 authored_datetime（aware）与涉及的文件路径列表。"""
    commit_obj = _open(root).commit(hexsha)
    return {
        "date": commit_obj.authored_datetime,
        "files": list(commit_obj.stats.files.keys()),
    }


def log_file(root: Path, rel_path: str, limit: int = 50) -> List[dict]:
    repo = _open(root)
    try:
        commits = repo.git.log("--follow", f"-{limit}", "--format=%H%x1f%an%x1f%ad%x1f%s", "--date=iso-strict", "--", rel_path)
    except GitCommandError:
        return []
    entries = []
    for line in commits.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            entries.append({
                "commit": parts[0],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3],
            })
    return entries


def diff_file(
    root: Path,
    rel_path: str,
    commit: str,
    compare: Optional[str] = None,
    context_lines: int = 3,
) -> str:
    """unified diff：compare 为空时与上一版本（commit^）比较。"""
    repo = _open(root)
    old = compare or f"{commit}^"
    try:
        text = repo.git.diff(
            f"{old}..{commit}",
            f"-U{context_lines}",
            "--no-color",
            "--",
            rel_path,
        )
    except GitCommandError as e:
        raise WikiGitError(f"生成 diff 失败: {e}")
    lines = text.splitlines()
    truncated = len(lines) > MAX_DIFF_LINES
    if truncated:
        lines = lines[:MAX_DIFF_LINES] + [f"... diff 超出 {MAX_DIFF_LINES} 行，已截断"]
    return "\n".join(lines)


def revert_file(
    root: Path,
    rel_path: str,
    commit: str,
    author_name: str,
    email_suffix: str = "wiki.local",
) -> str:
    """检出历史版本为新提交（不改写历史），返回新 commit hexsha。"""
    repo = _open(root)
    try:
        repo.git.checkout(commit, "--", rel_path)
    except GitCommandError as e:
        raise WikiGitError(f"回滚失败: {e}")
    message = f"revert: {rel_path} to {commit[:7]}"
    actor = _actor(author_name, email_suffix)
    c = repo.index.commit(message, author=actor, committer=actor)
    return c.hexsha


def move_file(root: Path, src: str, dst: str) -> None:
    repo = _open(root)
    dst_parent = (root / dst).parent
    dst_parent.mkdir(parents=True, exist_ok=True)
    try:
        repo.git.mv(src, dst)
    except GitCommandError:
        # 未入库的新文件 git mv 会失败，退回文件系统移动（commit 时 add -A 兜底）
        shutil.move(str(root / src), str(root / dst))


def remove_path(root: Path, rel_path: str, recursive: bool = False) -> None:
    target = root / rel_path
    if target.is_dir():
        if not recursive:
            raise WikiGitError("删除目录需要 recursive=true")
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


def pull(root: Path, author_name: str, email_suffix: str = "wiki.local") -> None:
    """pull --rebase。本地有未提交变更先自动提交；冲突时 abort 并抛出冲突文件列表。"""
    repo = _open(root)
    if has_changes(root):
        commit(root, "sync: auto commit before pull", author_name, email_suffix)
    try:
        repo.git.pull("--rebase")
    except GitCommandError as e:
        # 冲突：回滚 rebase，保持本地原状
        try:
            repo.git.rebase("--abort")
        except GitCommandError:
            pass
        raise WikiGitError(f"pull 发生冲突，已保持本地原状: {e}")


def push(root: Path, author_name: str, email_suffix: str = "wiki.local") -> None:
    repo = _open(root)
    try:
        repo.git.push()
    except GitCommandError:
        # non-fast-forward：pull --rebase 后重试一次，仍失败则抛给前端提示先 pull
        pull(root, author_name, email_suffix)
        try:
            repo.git.push()
        except GitCommandError as e:
            raise WikiGitError(f"push 被拒，请先执行 pull: {e}")


def status(root: Path) -> List[dict]:
    """工作区变更列表，用于「未提交变更」面板。"""
    repo = _open(root)
    out = repo.git.status("--porcelain")
    items = []
    for line in out.splitlines():
        if len(line) > 3:
            items.append({"code": line[:2], "path": line[3:].strip().strip('"').replace("\\", "/")})
    return items
