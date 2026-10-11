"""
Safe archive extraction for TAR and ZIP archives (§8.1 & §11).
Defends against:
- Directory traversal (.. path segments, absolute paths, drive letters)
- Symlink and hardlink attacks
- Device, socket, and FIFO files
- Zip-bomb attacks (compression ratio > 100:1, entry cap, total uncompressed size cap)
"""

import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import PurePosixPath

import structlog

from app.core.config import get_settings
from app.core.errors import ValidationFailedError

logger = structlog.get_logger(__name__)

ZIP_MAGIC = b"PK\x03\x04"
ZIP_EMPTY_MAGIC = b"PK\x05\x06"
GZIP_MAGIC = b"\x1f\x8b"


def is_valid_zip_magic(file_path: str) -> bool:
    """Checks if file starts with valid ZIP magic bytes."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            return header.startswith(ZIP_MAGIC) or header.startswith(ZIP_EMPTY_MAGIC)
    except Exception:
        return False


def is_valid_gzip_magic(file_path: str) -> bool:
    """Checks if file starts with valid GZIP magic bytes."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(2)
            return header.startswith(GZIP_MAGIC)
    except Exception:
        return False


def _validate_path_security(path_str: str) -> PurePosixPath:
    """
    Validates that a path is safe and contains no traversal sequences.
    """
    normalized = path_str.replace("\\", "/").strip()
    if not normalized:
        raise ValidationFailedError("Empty archive entry path.")

    # Rejection of absolute paths and drive letters
    if normalized.startswith("/") or normalized.startswith("\\"):
        raise ValidationFailedError(f"Malicious archive entry: absolute path '{path_str}'.")
    if len(normalized) > 1 and normalized[1] == ":" and normalized[0].isalpha():
        raise ValidationFailedError(f"Malicious archive entry: drive letter in path '{path_str}'.")

    posix = PurePosixPath(normalized)
    for part in posix.parts:
        if part in ("..", ""):
            raise ValidationFailedError(
                f"Malicious archive entry: path traversal '..' in '{path_str}'."
            )

    return posix


class SafeArchiveExtractor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.max_entries = self.settings.MAX_ARCHIVE_ENTRIES
        self.max_uncompressed_bytes = self.settings.MAX_UNCOMPRESSED_SIZE_MB * 1024 * 1024
        self.max_compression_ratio = 100.0

    def extract_tar(
        self,
        tar_path: str,
        destination_dir: str,
        strip_root_dir: bool = True,
    ) -> int:
        """
        Safely extracts a tar.gz / tar archive into destination_dir.
        Optionally strips the single top-level directory (e.g. owner-repo-sha/).
        Returns the number of files extracted.
        """
        temp_dir = tempfile.mkdtemp(prefix="repogpt_tar_")
        total_extracted_bytes = 0
        file_count = 0

        try:
            with tarfile.open(tar_path, "r:*") as tar:
                members = tar.getmembers()
                if len(members) > self.max_entries:
                    raise ValidationFailedError(
                        f"Archive entry count ({len(members)}) exceeds maximum permitted limit ({self.max_entries})."
                    )

                # Determine if there's a common top-level directory to strip
                root_prefix = None
                if strip_root_dir and members:
                    first_part = PurePosixPath(members[0].name.replace("\\", "/")).parts[0]
                    if all(
                        PurePosixPath(m.name.replace("\\", "/")).parts[0] == first_part
                        for m in members
                    ):
                        root_prefix = first_part

                for member in members:
                    # Security checks
                    if member.issym() or member.islnk():
                        raise ValidationFailedError(
                            f"Malicious archive entry: symlink or hardlink '{member.name}' is prohibited."
                        )
                    if member.isdev() or member.isfifo():
                        raise ValidationFailedError(
                            f"Malicious archive entry: device or FIFO file '{member.name}' is prohibited."
                        )

                    validated_path = _validate_path_security(member.name)
                    parts = list(validated_path.parts)
                    if root_prefix and len(parts) > 1 and parts[0] == root_prefix:
                        parts = parts[1:]
                    elif root_prefix and len(parts) == 1 and parts[0] == root_prefix:
                        continue  # Skip root folder itself

                    target_rel_path = "/".join(parts)
                    if not target_rel_path:
                        continue

                    # Uncompressed size check
                    total_extracted_bytes += member.size
                    if total_extracted_bytes > self.max_uncompressed_bytes:
                        raise ValidationFailedError(
                            f"Archive total uncompressed size exceeds limit of {self.settings.MAX_UNCOMPRESSED_SIZE_MB} MB."
                        )

                    # Extract file/dir
                    dest_path = os.path.join(temp_dir, *parts)
                    if member.isdir():
                        os.makedirs(dest_path, exist_ok=True)
                    elif member.isreg():
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        source_f = tar.extractfile(member)
                        if source_f is not None:
                            with source_f, open(dest_path, "wb") as dest_f:
                                shutil.copyfileobj(source_f, dest_f)
                            file_count += 1

            # Atomic move from temp_dir to destination_dir
            if os.path.exists(destination_dir):
                shutil.rmtree(destination_dir)
            os.makedirs(os.path.dirname(destination_dir), exist_ok=True)
            shutil.move(temp_dir, destination_dir)
            logger.info("tar_extracted_successfully", files=file_count, bytes=total_extracted_bytes)
            return file_count

        except Exception:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise

    def extract_zip(
        self,
        zip_path: str,
        destination_dir: str,
        strip_root_dir: bool = False,
    ) -> int:
        """
        Safely extracts a ZIP archive into destination_dir with full zip-bomb validation.
        Returns the number of files extracted.
        """
        temp_dir = tempfile.mkdtemp(prefix="repogpt_zip_")
        total_extracted_bytes = 0
        file_count = 0

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                infolist = zf.infolist()
                if len(infolist) > self.max_entries:
                    raise ValidationFailedError(
                        f"Archive entry count ({len(infolist)}) exceeds maximum permitted limit ({self.max_entries})."
                    )

                # Determine if there's a common top-level directory to strip
                root_prefix = None
                if strip_root_dir and infolist:
                    first_part = PurePosixPath(infolist[0].filename.replace("\\", "/")).parts[0]
                    if all(
                        PurePosixPath(info.filename.replace("\\", "/")).parts[0] == first_part
                        for info in infolist
                    ):
                        root_prefix = first_part

                for info in infolist:
                    filename = info.filename
                    # Check for symlink in external_attr (Unix mode 0o120000)
                    unix_mode = (info.external_attr >> 16) & 0o177777
                    if (unix_mode & 0o170000) == 0o120000:
                        raise ValidationFailedError(
                            f"Malicious archive entry: symlink '{filename}' is prohibited."
                        )

                    validated_path = _validate_path_security(filename)

                    # Zip-bomb defense: check compression ratio
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > self.max_compression_ratio:
                            raise ValidationFailedError(
                                f"Malicious archive entry: compression ratio ({ratio:.1f}:1) on '{filename}' "
                                f"exceeds safety threshold ({self.max_compression_ratio:.0f}:1). Potential zip-bomb detected."
                            )

                    total_extracted_bytes += info.file_size
                    if total_extracted_bytes > self.max_uncompressed_bytes:
                        raise ValidationFailedError(
                            f"Archive total uncompressed size exceeds limit of {self.settings.MAX_UNCOMPRESSED_SIZE_MB} MB."
                        )

                    parts = list(validated_path.parts)
                    if root_prefix and len(parts) > 1 and parts[0] == root_prefix:
                        parts = parts[1:]
                    elif root_prefix and len(parts) == 1 and parts[0] == root_prefix:
                        continue

                    target_rel_path = "/".join(parts)
                    if not target_rel_path:
                        continue

                    dest_path = os.path.join(temp_dir, *parts)
                    if info.is_dir() or filename.endswith("/"):
                        os.makedirs(dest_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with zf.open(info) as src, open(dest_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        file_count += 1

            if os.path.exists(destination_dir):
                shutil.rmtree(destination_dir)
            os.makedirs(os.path.dirname(destination_dir), exist_ok=True)
            shutil.move(temp_dir, destination_dir)
            logger.info("zip_extracted_successfully", files=file_count, bytes=total_extracted_bytes)
            return file_count

        except Exception:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise
