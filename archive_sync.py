# -*- coding: utf-8 -*-
"""
采集后把 output/ 归档镜像推送到 archive 分支。

通过 git worktree 在独立目录提交,主工作区(master)不受影响。
任何失败只记录日志,不影响采集主流程。
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from config import (
    ARCHIVE_GIT_BRANCH,
    ARCHIVE_GIT_DIR,
    ARCHIVE_GIT_ENABLED,
    ARCHIVE_GIT_REMOTE,
    ARCHIVE_GIT_WORKTREE,
    OUTPUT_ARCHIVE_DIR,
)

logger = logging.getLogger(__name__)


def _run(cmd, cwd=None):
    """运行任意命令,返回 (returncode, stdout, stderr),均去除首尾空白。"""
    proc = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _run_git(args, cwd=None):
    """运行 git 命令,cwd 非 None 时加 -C 指定工作目录。"""
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", str(cwd)]
    return _run(cmd + list(args))


def _repo_root():
    """返回当前 git 仓库根目录(基于 cwd 探测)。"""
    code, stdout, stderr = _run_git(["rev-parse", "--show-toplevel"])
    if code != 0:
        raise RuntimeError("无法定位 git 仓库根目录: {}".format(stderr))
    return Path(stdout)


ARCHIVE_README = """# Archive 分支

本分支由采集流程自动写入,存放 `output/` 的镜像归档数据。

- 目录结构:`archive/<source_id>/<YYYY-MM-DD>/<batch>.json` + `archive/latest.json`
- 生成频率:跟随采集调度(默认每天 3 次)
- 请勿手动编辑;数据由 `archive_sync.py` 维护
"""


def _is_worktree(path):
    """判断路径是否是一个已检出的 git worktree。"""
    path = Path(path)
    return path.exists() and (path / ".git").exists()


def _local_branch_exists(repo_root, branch):
    code, _, _ = _run_git(["rev-parse", "--verify", branch], cwd=repo_root)
    return code == 0


def _remote_branch_exists(repo_root, remote, branch):
    code, stdout, _ = _run_git(["ls-remote", "--heads", remote, branch], cwd=repo_root)
    return code == 0 and bool(stdout)


def _pick_base(repo_root, remote):
    """挑选创建 archive 分支的起点,优先 remote/master。"""
    for candidate in ["{}/master".format(remote), "master", "HEAD"]:
        code, _, _ = _run_git(["rev-parse", "--verify", candidate], cwd=repo_root)
        if code == 0:
            return candidate
    return "HEAD"


def _ensure_readme(worktree_path):
    """首次创建 worktree 后,在根目录写入说明文件 ARCHIVE.md。

    用 ARCHIVE.md 而非 README.md,避免覆盖 master 继承下来的源码 README。
    """
    readme = Path(worktree_path) / "ARCHIVE.md"
    if readme.exists():
        return
    readme.write_text(ARCHIVE_README, encoding="utf-8")


def _ensure_worktree(repo_root, worktree_path, branch, remote):
    """确保 worktree 与 archive 分支存在,返回 worktree 绝对路径。

    - worktree 已存在:直接复用。
    - 分支已存在于本地或远端:检出该分支。
    - 否则:基于 remote/master(回退 master/HEAD)新建分支。
    """
    worktree_path = Path(worktree_path).resolve()

    if _is_worktree(worktree_path):
        return worktree_path

    if _local_branch_exists(repo_root, branch):
        code, _, err = _run_git(
            ["worktree", "add", str(worktree_path), branch], cwd=repo_root,
        )
    elif _remote_branch_exists(repo_root, remote, branch):
        code, _, err = _run_git(
            ["worktree", "add", str(worktree_path), "{}/{}".format(remote, branch)],
            cwd=repo_root,
        )
    else:
        base = _pick_base(repo_root, remote)
        code, _, err = _run_git(
            ["worktree", "add", "-b", branch, str(worktree_path), base], cwd=repo_root,
        )

    if code != 0:
        raise RuntimeError("创建 worktree 失败: {}".format(err))

    _ensure_readme(worktree_path)
    return worktree_path
