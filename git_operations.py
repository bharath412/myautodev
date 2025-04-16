# git_operations.py
import subprocess
import streamlit as st
from pathlib import Path

def run_git_command(command, cwd, status_placeholder=None):
    """Run a git command and return output and success status"""
    try:
        # Convert Path object to string for subprocess
        cwd_str = str(cwd)
        
        # Add git command prefix if not present
        if not command[0].startswith('git'):
            command = ['git'] + command

        process = subprocess.run(
            command,
            cwd=cwd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        output = process.stdout + process.stderr
        if status_placeholder:
            status_placeholder.success(f"✅ {' '.join(command)}")
            status_placeholder.code(output)  # Show command output
        return output, True
    except subprocess.CalledProcessError as e:
        error_msg = f"Error: {e.stderr}"
        if status_placeholder:
            status_placeholder.error(f"❌ {' '.join(command)} failed")
            status_placeholder.code(error_msg)
        return error_msg, False

def ensure_git_configured(cwd):
    """Verify git configuration"""
    try:
        # Check git installation
        version_cmd = subprocess.run(
            ['git', '--version'], 
            capture_output=True, 
            text=True
        )
        if version_cmd.returncode != 0:
            return False, "Git is not installed or not in PATH"

        # Check repository
        git_dir = Path(cwd) / '.git'
        if not git_dir.is_dir():
            return False, f"Not a git repository in {cwd}"

        # Check config
        config_cmd = subprocess.run(
            ['git', 'config', '--list'],
            cwd=str(cwd),
            capture_output=True,
            text=True
        )
        
        if 'user.name' not in config_cmd.stdout or 'user.email' not in config_cmd.stdout:
            return False, "Git user.name or user.email not configured"

        # Check remote
        remote_cmd = subprocess.run(
            ['git', 'remote', '-v'],
            cwd=str(cwd),
            capture_output=True,
            text=True
        )
        
        if 'origin' not in remote_cmd.stdout:
            return False, "No remote 'origin' configured"

        return True, "Git properly configured"
    except Exception as e:
        return False, f"Git configuration error: {str(e)}"

def execute_git_flow(project_root, commit_message, placeholder):
    """Execute git add, commit, push flow"""
    if not isinstance(project_root, Path):
        project_root = Path(project_root)

    # Ensure we're in a git repository
    if not (project_root / '.git').is_dir():
        placeholder.error("Not a git repository!")
        return False, "Not a git repository"

    # 1. Git status
    status_output, status_ok = run_git_command(['status'], project_root, placeholder)
    if not status_ok:
        return False, status_output

    # 2. Git add
    add_output, add_ok = run_git_command(['add', '.'], project_root, placeholder)
    if not add_ok:
        return False, add_output

    # 3. Git status after add
    status_output, _ = run_git_command(['status'], project_root, placeholder)
    if "nothing to commit" in status_output:
        placeholder.info("No changes to commit")
        return True, "No changes to commit"

    # 4. Git commit
    commit_output, commit_ok = run_git_command(
        ['commit', '-m', commit_message], 
        project_root, 
        placeholder
    )
    if not commit_ok:
        return False, commit_output

    # 5. Git pull to avoid conflicts
    pull_output, pull_ok = run_git_command(
        ['pull', 'origin', 'main'], 
        project_root, 
        placeholder
    )
    if not pull_ok:
        return False, pull_output

    # 6. Git push
    push_output, push_ok = run_git_command(
        ['push', 'origin', 'main'], 
        project_root, 
        placeholder
    )
    if not push_ok:
        return False, push_output

    return True, "Git operations completed successfully"