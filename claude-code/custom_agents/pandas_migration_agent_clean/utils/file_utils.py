"""File handling utilities."""

import os
import shutil
from typing import Optional


def read_file(file_path: str) -> str:
    """Read a file with proper encoding handling."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # If all encodings fail, read as binary and decode with errors='ignore'
    with open(file_path, 'rb') as f:
        return f.read().decode('utf-8', errors='ignore')


def write_file(file_path: str, content: str) -> None:
    """Write content to a file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def create_backup(file_path: str) -> str:
    """Create a backup of the file."""
    backup_path = f"{file_path}.backup"
    
    # If backup already exists, add a number
    if os.path.exists(backup_path):
        i = 1
        while os.path.exists(f"{file_path}.backup{i}"):
            i += 1
        backup_path = f"{file_path}.backup{i}"
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def restore_backup(file_path: str, backup_path: str) -> None:
    """Restore a file from backup."""
    shutil.copy2(backup_path, file_path)