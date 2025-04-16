# git_operations.py
import subprocess
import streamlit as st
from pathlib import Path
import subprocess
import platform
from pathlib import Path
import shlex
import streamlit as st

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

# Assuming PROJECT_ROOT is defined in your main script or passed as an argument
# Example (you might not define it here):
# PROJECT_ROOT = Path("./my_heroku_app")

def run_command_separate_terminal(project_root,command_list, cwd):
    """Tries to run a command in a new terminal window."""
    # Security Check on CWD
    if not Path(cwd).resolve().is_relative_to(project_root.resolve()):
        st.error(f"Security Error: Attempting to run command outside project root CWD: {cwd}")
        return False

    system = platform.system()
    st.write(f"Attempting to run `{' '.join(command_list)}` in new terminal (OS: {system}, CWD: {cwd})")
    try:
        if system == "Windows":
            full_command = "cmd /c start cmd /k " + " ".join(command_list)
            subprocess.Popen(full_command, cwd=cwd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True
        elif system == "Darwin": # macOS
            cwd_escaped = shlex.quote(str(cwd))
            cmd_string = " ".join(command_list)
            cmd_escaped_applescript = cmd_string.replace('\\', '\\\\').replace('"', '\\"')
            script = f'tell application "Terminal" to do script "cd {cwd_escaped} && {cmd_escaped_applescript}" activate'
            proc = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=10) # Add timeout
            if proc.returncode != 0:
                st.error(f"osascript failed: {stderr.decode(errors='replace')}")
                return False
            return True
        elif system == "Linux":
            quoted_cmd_list = [shlex.quote(part) for part in command_list]
            quoted_cwd = shlex.quote(str(cwd))
            cmd_string_linux = " ".join(quoted_cmd_list)

            terminals = [
                {"cmd": ["gnome-terminal", "--working-directory", str(cwd), "--"] + command_list},
                {"cmd": ["konsole", "--workdir", str(cwd), "-e"] + command_list},
                {"cmd": ["xterm", "-hold", "-e", f"sh -c 'cd {quoted_cwd} && {cmd_string_linux}'"]}, # Wrap in sh -c
                {"cmd": ["terminator", "--working-directory", str(cwd), "-e", cmd_string_linux, "-x", "bash", "-c", "read -p 'Press Enter to close...'"]}, # Example for terminator
            ]
            launched = False
            for term_info in terminals:
                term_cmd = term_info["cmd"]
                try:
                    st.write(f"Trying terminal command: {' '.join(term_cmd)}")
                    subprocess.Popen(term_cmd)
                    launched = True
                    break # Success
                except FileNotFoundError:
                    pass # Try the next terminal
                except Exception as e:
                    st.warning(f"Failed to launch with {term_cmd[0]}: {e}")
                    # Continue trying others

            if not launched:
                st.error("Could not find a known terminal emulator (gnome-terminal, konsole, xterm, terminator). Please run the command manually.")
                return False
            return True # Launched successfully with one of the terminals
        else:
            st.error(f"Unsupported operating system for separate terminal: {system}")
            return False
    except subprocess.TimeoutExpired:
        st.error("Timed out waiting for terminal command to launch.")
    except Exception as e:
        st.error(f"Failed to start command in new terminal: {e}")
    return False

def deploy_to_heroku_separate_terminal(project_root):
    """Opens a new terminal and runs 'git push heroku main' in the given project root."""
    command = ["git", "push", "heroku", "main"]
    return run_command_separate_terminal(project_root,command, project_root)