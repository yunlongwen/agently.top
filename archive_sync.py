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
