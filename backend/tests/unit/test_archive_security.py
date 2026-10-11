"""
Unit tests for archive security defenses (§8.1 & §11).
Tests rejection of:
- Path traversal ('../evil.py')
- Absolute paths ('/etc/passwd', 'C:\\malicious.py')
- Symlinks and hardlinks
- Zip-bomb attacks (extreme compression ratios)
"""

import io
import os
import tarfile
import tempfile
import zipfile

import pytest

from app.core.errors import ValidationFailedError
from app.services.ingestion.archive import SafeArchiveExtractor


def test_reject_zip_path_traversal():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "traversal.zip")
        dest_dir = os.path.join(tmpdir, "output")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../escape.py", "malicious_payload = True\n")

        with pytest.raises(ValidationFailedError, match="path traversal"):
            extractor.extract_zip(zip_path, dest_dir)


def test_reject_zip_absolute_path():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "absolute.zip")
        dest_dir = os.path.join(tmpdir, "output")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", "root:x:0:0...\n")

        with pytest.raises(ValidationFailedError, match="absolute path"):
            extractor.extract_zip(zip_path, dest_dir)


def test_reject_zip_drive_letter():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "drive.zip")
        dest_dir = os.path.join(tmpdir, "output")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("C:/Windows/System32/evil.dll", "malicious\n")

        with pytest.raises(ValidationFailedError, match="drive letter"):
            extractor.extract_zip(zip_path, dest_dir)


def test_reject_zip_symlink():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "symlink.zip")
        dest_dir = os.path.join(tmpdir, "output")

        info = zipfile.ZipInfo("symlink_target")
        # Unix file mode for symlink: 0o120777
        info.external_attr = 0o120777 << 16

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(info, "/etc/passwd")

        with pytest.raises(ValidationFailedError, match="symlink"):
            extractor.extract_zip(zip_path, dest_dir)


def test_reject_zip_bomb_compression_ratio():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "bomb.zip")
        dest_dir = os.path.join(tmpdir, "output")

        # 5 MB of zeroes compresses to under 5 KB (ratio > 1000:1)
        zeroes = b"\x00" * (5 * 1024 * 1024)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("huge_zeroes.dat", zeroes)

        with pytest.raises(ValidationFailedError, match="compression ratio"):
            extractor.extract_zip(zip_path, dest_dir)


def test_reject_tar_path_traversal():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "traversal.tar.gz")
        dest_dir = os.path.join(tmpdir, "output")

        with tarfile.open(tar_path, "w:gz") as tar:
            data = b"print('hacked')"
            ti = tarfile.TarInfo(name="../escaped.py")
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))

        with pytest.raises(ValidationFailedError, match="path traversal"):
            extractor.extract_tar(tar_path, dest_dir)


def test_reject_tar_symlink():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "symlink.tar.gz")
        dest_dir = os.path.join(tmpdir, "output")

        with tarfile.open(tar_path, "w:gz") as tar:
            ti = tarfile.TarInfo(name="symlink_link")
            ti.type = tarfile.SYMTYPE
            ti.linkname = "/etc/passwd"
            tar.addfile(ti)

        with pytest.raises(ValidationFailedError, match="symlink or hardlink"):
            extractor.extract_tar(tar_path, dest_dir)


def test_safe_tar_and_zip_extraction():
    extractor = SafeArchiveExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "safe.zip")
        dest_dir = os.path.join(tmpdir, "output")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("src/main.py", "print('hello world')\n")
            zf.writestr("README.md", "# Test Readme\n")

        count = extractor.extract_zip(zip_path, dest_dir)
        assert count == 2
        assert os.path.isfile(os.path.join(dest_dir, "src", "main.py"))
        assert os.path.isfile(os.path.join(dest_dir, "README.md"))
