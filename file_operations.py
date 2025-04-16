from pathlib import Path
import re
import streamlit as st
from config import PROJECT_ROOT, JAVA_SRC_DIRS, STATIC_SRC_DIR, relative_robot_path_str

def find_project_file(filename_or_path):
    """Find files within the project structure"""
    target_path_obj = Path(filename_or_path)

    # Security checks and standard directory search implementation
    # [Previous implementation remains the same]

def get_file_language(file_path):
    """Determine file language from extension"""
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    ext_map = {
        '.java': 'java',
        '.html': 'html',
        '.css': 'css',
        '.js': 'javascript',
        '.robot': 'robotframework',
        '.xml': 'xml',
        '.properties': 'properties',
        '.md': 'markdown',
    }
    return ext_map.get(file_path.suffix.lower(), 'plaintext')

def read_file_content(file_path):
    """Read file content safely"""
    try:
        if not file_path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
            st.error(f"Security Error: Attempted to read file outside project root: {file_path}")
            return None
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        st.error(f"Error reading file {file_path}: {e}")
        return None

def write_changes_to_file(file_path_str, new_content):
    """Write content to file safely"""
    try:
        file_path = Path(file_path_str)
        if not file_path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
            st.error(f"Security Error: Attempted to write file outside project root: {file_path}")
            return False

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Error writing changes to {file_path_str}: {e}")
        return False