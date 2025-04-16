import subprocess
import platform
import socket
import time
import shlex
import streamlit as st
from pathlib import Path
from config import PROJECT_ROOT

def check_port(host="127.0.0.1", port=8081, retries=30, delay=2):
    """Check if a port is open and accepting connections"""
    st.write(f"Checking if port {host}:{port} is open...")
    for i in range(retries):
        try:
            with socket.create_connection((host, port), timeout=1):
                st.write(f"Port {port} check {i+1}/{retries}: Connected!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            pass
        except Exception as e:
            st.warning(f"Port check {i+1}/{retries} encountered error: {e}")
        if i < retries - 1:
            time.sleep(delay)
    return False

def run_command_separate_terminal(command_list, cwd):
    """Run command in a new terminal window"""
    if not Path(cwd).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        st.error(f"Security Error: Attempting to run command outside project root CWD: {cwd}")
        return False

    system = platform.system()
    st.write(f"Attempting to run `{' '.join(command_list)}` in new terminal (OS: {system}, CWD: {cwd})")
    
    try:
        if system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", " ".join(command_list)], 
                           cwd=cwd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif system == "Darwin":  # macOS
            run_macos_terminal(command_list, cwd)
        elif system == "Linux":
            run_linux_terminal(command_list, cwd)
        else:
            st.error(f"Unsupported operating system: {system}")
            return False
        return True
    except Exception as e:
        st.error(f"Failed to start command in new terminal: {e}")
        return False

def run_robot_tests(test_path, cwd):
    """Run Robot Framework tests"""
    if not isinstance(test_path, Path):
        test_path = Path(test_path)

    if not test_path.exists():
        err_msg = f"Robot test path does not exist: {test_path}"
        st.error(err_msg)
        return False, f"ERROR: {err_msg}"

    if not Path(cwd).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        err_msg = f"Security Error: Attempting to run tests outside project root CWD: {cwd}"
        st.error(err_msg)
        return False, f"ERROR: {err_msg}"

    return execute_robot_tests(test_path, cwd)

def execute_robot_tests(test_path, cwd):
    """Execute Robot Framework tests with proper output handling"""
    command = ["robot", str(test_path)]
    st.info(f"Running Robot tests: `{' '.join(command)}` in `{cwd}`")
    
    process = None
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        output = handle_test_output(process)
        return_code = process.wait(timeout=5)
        success = return_code == 0
        
        return success, output
    except Exception as e:
        return False, f"Error executing tests: {str(e)}"
    finally:
        if process and process.poll() is None:
            process.terminate()