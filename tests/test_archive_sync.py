# -*- coding: utf-8 -*-
"""
archive_sync 模块测试用例。

用临时目录搭建本地 git 仓库 + bare remote,不依赖真实 GitHub。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, ".")

from archive_sync import _run_git, _repo_root  # noqa: E402
from archive_sync import _ensure_worktree  # noqa: E402


def _git(args, cwd):
    """测试用:以 check 模式跑 git,失败直接抛错。"""
    subprocess.run(["git"] + list(args), cwd=str(cwd), check=True, capture_output=True, text=True)


def _make_repo(tmp_path):
    """在 tmp_path 下建一个带初始提交与 bare remote 的仓库,返回 (repo, remote)。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    remote = tmp_path / "remote.git"
    _git(["init", "--bare", str(remote)], tmp_path)
    _git(["remote", "add", "origin", str(remote)], repo)
    _git(["push", "-u", "origin", "master"], repo)
    return repo, remote


class TestRunGit(unittest.TestCase):
    def test_run_git_returns_version(self):
        code, stdout, _ = _run_git(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("git version", stdout)

    def test_repo_root_locates_cwd_repository(self):
        root = _repo_root()
        self.assertTrue(root.exists())
        self.assertEqual(root.resolve(), Path(".").resolve())


class TestEnsureWorktree(unittest.TestCase):
    def test_creates_worktree_and_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = _make_repo(Path(tmp))
            worktree = repo / ".archive-worktree"
            result = _ensure_worktree(repo, worktree, "archive", "origin")
            self.assertTrue((worktree / ".git").exists())
            self.assertEqual(result, worktree.resolve())
            # archive 分支已在本地存在
            code, _, _ = _run_git(["rev-parse", "--verify", "archive"], cwd=repo)
            self.assertEqual(code, 0)
            # ARCHIVE.md 已写入 worktree 根
            self.assertTrue((worktree / "ARCHIVE.md").exists())

    def test_idempotent_on_second_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = _make_repo(Path(tmp))
            worktree = repo / ".archive-worktree"
            _ensure_worktree(repo, worktree, "archive", "origin")
            # 第二次调用不抛异常(worktree 已存在直接复用)
            _ensure_worktree(repo, worktree, "archive", "origin")
            self.assertTrue((worktree / ".git").exists())


if __name__ == "__main__":
    unittest.main()
