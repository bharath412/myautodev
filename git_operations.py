# git_operations.py
import subprocess
import streamlit as st
from pathlib import Path

def run_git_command(command, cwd, placeholder):
    """Runs a git command and captures output."""
    try:
        placeholder.write(f"> git {' '.join(command)}")
        process = subprocess.run(
            ["git"] + command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True, # Raise exception on non-zero exit code
            encoding='utf-8',
            errors='replace'
        )
        output = process.stdout.strip()
        if output:
             placeholder.code(output, language='bash')
        return True, process.stdout + process.stderr # Return full output including stderr
    except FileNotFoundError:
        err_msg = "Error: 'git' command not found. Is Git installed and in PATH?"
        placeholder.error(err_msg)
        return False, err_msg
    except subprocess.CalledProcessError as e:
        err_msg = f"Git command failed:\n{e.stderr}\n{e.stdout}"
        placeholder.error(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"An error occurred during git operation: {e}"
        placeholder.error(err_msg)
        return False, err_msg

def execute_git_flow(repo_url, commit_message, placeholder):
    """Placeholder for git add, commit, push flow."""
    repo_path = Path(".") # Assuming run from project root
    full_log = f"--- Git Operations Log for commit: '{commit_message}' ---\n"
    success_overall = True

    placeholder.info("Running Git operations...")

    # Git Add
    success, log = run_git_command(["add", "."], repo_path, placeholder)
    full_log += f"\n> git add .\n{log}\n"
    if not success:
        success_overall = False
        placeholder.error("Git add failed.")
        return False, full_log

    # Git Commit
    success, log = run_git_command(["commit", "-m", commit_message], repo_path, placeholder)
    full_log += f"\n> git commit -m \"{commit_message}\"\n{log}\n"
    if not success:
        # It might fail if there's nothing to commit, which isn't necessarily an error
        if "nothing to commit, working tree clean" in log:
             placeholder.warning("Nothing new to commit.")
             # Continue as this is not a failure in the flow
        else:
             success_overall = False
             placeholder.error("Git commit failed.")
             return False, full_log

    # Git Push (assuming 'origin' and 'main' or 'master' branch)
    # You might need to determine the current branch dynamically
    current_branch = 'main' # Or 'master', or detect dynamically
    success, log = run_git_command(["push", "origin", current_branch], repo_path, placeholder)
    full_log += f"\n> git push origin {current_branch}\n{log}\n"
    if not success:
        success_overall = False
        placeholder.error("Git push failed.")
        return False, full_log

    if success_overall:
        placeholder.success("Git operations completed successfully.")
    else:
         placeholder.error("One or more Git operations failed.")


    return success_overall, full_log + "\n--- End Git Log ---"