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

from infrastructure.archive_sync import _run_git, _repo_root  # noqa: E402
from infrastructure.archive_sync import _ensure_worktree  # noqa: E402
from infrastructure.archive_sync import _sync_output  # noqa: E402
from infrastructure.archive_sync import _commit_and_push  # noqa: E402
from infrastructure.archive_sync import sync_archive_to_git  # noqa: E402


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


class TestSyncOutput(unittest.TestCase):
    def _make_output(self, tmp):
        output = Path(tmp) / "output"
        (output / "github-daily" / "2026-06-17").mkdir(parents=True)
        (output / "github-daily" / "2026-06-17" / "01.json").write_text("{}", encoding="utf-8")
        (output / "latest.json").write_text("{}", encoding="utf-8")
        return output

    def test_mirrors_output_to_archive_via_shutil(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._make_output(tmp)
            archive = Path(tmp) / "archive"
            with patch("archive_sync._has_rsync", return_value=False):
                _sync_output(output, archive)
            self.assertTrue((archive / "latest.json").exists())
            self.assertTrue((archive / "github-daily" / "2026-06-17" / "01.json").exists())

    def test_uses_rsync_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._make_output(tmp)
            archive = Path(tmp) / "archive"
            with patch("archive_sync._has_rsync", return_value=True), \
                 patch("archive_sync._run") as mock_run:
                mock_run.return_value = (0, "", "")
                _sync_output(output, archive)
            invoked = [call.args[0] for call in mock_run.call_args_list]
            self.assertTrue(any(cmd[0] == "rsync" for cmd in invoked))


class TestCommitAndPush(unittest.TestCase):
    def _setup(self, tmp):
        repo, remote = _make_repo(Path(tmp))
        worktree = repo / ".archive-worktree"
        _ensure_worktree(repo, worktree, "archive", "origin")
        return repo, remote, worktree

    def test_commits_and_pushes_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote, worktree = self._setup(tmp)
            archive = worktree / "archive"
            archive.mkdir()
            (archive / "01.json").write_text("{}", encoding="utf-8")
            pushed = _commit_and_push(worktree, "archive", "origin", item_count=5)
            self.assertTrue(pushed)
            # bare remote 已收到 archive 分支
            code, stdout, _ = _run_git(["ls-remote", "--heads", "origin", "archive"], cwd=repo)
            self.assertTrue(stdout.strip())

    def test_skips_commit_when_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote, worktree = self._setup(tmp)
            # 首次:提交 ARCHIVE.md(_ensure_worktree 写入)
            _commit_and_push(worktree, "archive", "origin", item_count=1)
            # 再次:无新变更,应跳过
            pushed = _commit_and_push(worktree, "archive", "origin", item_count=1)
            self.assertFalse(pushed)


class TestSyncArchiveToGit(unittest.TestCase):
    def test_pushes_archive_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote = _make_repo(Path(tmp))
            output = repo / "output"
            (output / "tldr-ai" / "2026-06-17").mkdir(parents=True)
            (output / "tldr-ai" / "2026-06-17" / "01.json").write_text("{}", encoding="utf-8")
            (output / "latest.json").write_text("{}", encoding="utf-8")
            with patch("archive_sync.ARCHIVE_GIT_ENABLED", True), \
                 patch("archive_sync._repo_root", return_value=repo), \
                 patch("archive_sync._has_rsync", return_value=False):
                result = sync_archive_to_git(item_count=1)
            self.assertTrue(result)
            code, stdout, _ = _run_git(["ls-remote", "--heads", "origin", "archive"], cwd=repo)
            self.assertTrue(stdout.strip())

    def test_skips_when_disabled(self):
        with patch("archive_sync.ARCHIVE_GIT_ENABLED", False):
            result = sync_archive_to_git()
        self.assertFalse(result)

    def test_swallows_exceptions(self):
        with patch("archive_sync.ARCHIVE_GIT_ENABLED", True), \
             patch("archive_sync._repo_root", side_effect=RuntimeError("boom")):
            result = sync_archive_to_git()  # 不得抛出
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
