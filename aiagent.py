# -*- coding: utf-8 -*-
# filename: aiagent.txt
import streamlit as st
import subprocess
import requests
import time
import psutil
import os
import signal
import threading
from io import StringIO
import google.generativeai as genai
# import os # Duplicate import removed
import re
# import time # Duplicate import removed
import socket
# import subprocess # Duplicate import removed
import platform
from pathlib import Path
import shlex # <-- Import shlex for Linux command quoting
import git_operations # <-- Import the git operations module

# --- Configuration ---


# 1. API Key
try:
    # Attempt to get API key from Streamlit secrets first
    API_KEY = st.secrets.get("GEMINI_API_KEY")
    if not API_KEY:
        # Fallback to environment variable if not in secrets
        API_KEY = os.environ.get("GEMINI_API_KEY")
except AttributeError:
     # Handle case where st.secrets might not be available (e.g., local testing without secrets.toml)
     API_KEY = os.environ.get("GEMINI_API_KEY")


if not API_KEY:
    st.error("🚨 Gemini API Key not found! Please set it in Streamlit secrets (`.streamlit/secrets.toml`) or as an environment variable (`GEMINI_API_KEY`).")
    st.stop()

genai.configure(api_key=API_KEY)

# 2. Project Path
PROJECT_ROOT_PATH = "E:/ERP/dev/CursorAI2/myautodev" # <-- Your project root
PROJECT_ROOT = Path(PROJECT_ROOT_PATH) # Use Path object
if not PROJECT_ROOT.is_dir():
    st.error(f"🚨 Project Root Path not found or is not a directory: {PROJECT_ROOT_PATH}")
    st.warning("Please update the `PROJECT_ROOT_PATH` variable in the script.")
    st.stop()
# 2. Git Configuration
GIT_REPO_URL = "https://github.com/bharath412/myautodev.git" # Replace if needed
GIT_COMMIT_MESSAGE = "feat: AI-assisted code changes and test updates"# Define common source directories
JAVA_SRC_DIRS = ['src/main/java', 'src/test/java']
STATIC_SRC_DIR = 'src/main/resources/static' # <--- Static dir

# 3. Robot Framework Tests Path
ROBOT_TESTS_PATH_STR = "E:/ERP/dev/CursorAI2/myautodev/src/test/robotframework" # Using full path now for clarity
full_robot_path = Path(ROBOT_TESTS_PATH_STR) # Use the full path directly
relative_robot_path_str = "src/test/robotframework" # Define the typical relative path
if not full_robot_path.is_dir():
    check_relative_path = PROJECT_ROOT / relative_robot_path_str
    if check_relative_path.is_dir():
        full_robot_path = check_relative_path
        st.info(f"Using relative Robot path: {full_robot_path}")
    else:
        st.warning(f"🚨 Robot Framework tests path not found at {ROBOT_TESTS_PATH_STR} or relative path {relative_robot_path_str}. 'run myapp' test execution will be skipped.")
        # Not stopping the app, but warning the user.

# 4. Gemini Model Configuration
MODEL_NAME = "gemini-1.5-pro-latest"
generation_config = { "temperature": 0.7, "top_p": 1.0, "top_k": 1, "max_output_tokens": 8192, }
safety_settings = [ {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, ]

# --- Helper Functions ---

def find_project_file(filename_or_path):
    """Tries to find Java, HTML, CSS, or JS files within standard project locations."""
    target_path_obj = Path(filename_or_path)

    # 1. Check if it's already an absolute path within the project
    try:
        if target_path_obj.is_absolute() and target_path_obj.is_relative_to(PROJECT_ROOT):
            if target_path_obj.is_file():
                return target_path_obj
    except ValueError: # Not relative to project root
        pass
    except SecurityError: # Handle potential security issues with is_relative_to
        st.warning(f"Security check failed for path: {filename_or_path}")
        return None


    # 2. Check relative path from project root (assuming full relative path is given)
    try:
        relative_target = PROJECT_ROOT / filename_or_path
        # Security: Ensure resolved path is still within PROJECT_ROOT
        if relative_target.is_file() and relative_target.resolve().is_relative_to(PROJECT_ROOT.resolve()):
             return relative_target
    except Exception: # Catch potential errors during path resolution/check
         pass # If fails, continue searching specific dirs


    # 3. Search specific directories based on extension guess or common names
    ext = target_path_obj.suffix.lower()
    fname = target_path_obj.name

    # Basic check for potentially malicious filenames (e.g., trying to access parent dirs)
    if ".." in fname or "/" in fname or "\\" in fname:
         st.warning(f"Skipping potentially unsafe filename for search: {fname}")
         return None


    search_dirs = []
    search_patterns = []

    if ext == '.java' or (not ext and filename_or_path and filename_or_path[0].isupper()): # Guess Java if no extension and starts with capital
        search_dirs = [PROJECT_ROOT / d for d in JAVA_SRC_DIRS]
        search_patterns.append(f"**/{fname}") # Search by name only
        if not ext: # If no extension given, try adding .java
             search_patterns.append(f"**/{fname}.java")
    elif ext in ['.html', '.css', '.js'] or fname in ['index.html', 'styles.css', 'script.js', 'task.html']: # Added task.html
        search_dirs = [PROJECT_ROOT / STATIC_SRC_DIR]
        search_patterns.append(f"**/{fname}") # Search by name recursively


    for start_dir in search_dirs:
        if start_dir.is_dir():
            for pattern in search_patterns:
                try:
                    # Use rglob for recursive search
                    # Security: Ensure found files are within the start_dir (already checked if it's within PROJECT_ROOT)
                    found_files = [f for f in start_dir.rglob(pattern) if f.is_file() and f.resolve().is_relative_to(start_dir.resolve())]
                    if found_files:
                        # Optional: Add logic here if multiple files match (e.g., warn user, pick first)
                        return found_files[0] # Return the first match
                except Exception as e:
                     st.warning(f"Error searching in {start_dir} with pattern {pattern}: {e}")


    # Fallback: Try searching directly under PROJECT_ROOT if file name has extension
    # This helps if user provides a relative path like 'src/main/java/com/example/MyFile.java'
    # that wasn't caught by check #2
    if ext:
        try:
            potential_file = PROJECT_ROOT / filename_or_path
            # Security Check
            if potential_file.is_file() and potential_file.resolve().is_relative_to(PROJECT_ROOT.resolve()):
                return potential_file
        except Exception:
             pass


    return None # Not found

def get_file_language(file_path):
    """Guesses language from file extension."""
    # Ensure file_path is a Path object
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
        # Add more if needed
    }
    return ext_map.get(file_path.suffix.lower(), 'plaintext') # Default to plaintext


def read_file_content(file_path):
    """Reads content from a file path (Path object)."""
    try:
        # Security: Double-check the path is within the project before reading
        if not file_path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
             st.error(f"Security Error: Attempted to read file outside project root: {file_path}")
             return None
        return file_path.read_text(encoding='utf-8')
    except Exception as e:
        st.error(f"Error reading file {file_path}: {e}")
        return None

def parse_gemini_response(response_text):
    """
    Parses the Gemini response to extract file path, language, and code block.
    Attempts to determine the correct absolute path based on the relative path
    and standard project structure.
    """
    parsed_data = []
    # Regex to find file blocks and capture language tag
    # Added common file types like robot, xml, properties, md
    pattern = re.compile(
         r"--- START FILE: (.*?) ---\s*```(java|html|css|javascript|robotframework|xml|properties|md|)?\s*(.*?)\s*```\s*--- END FILE: \1 ---",
        re.DOTALL | re.IGNORECASE
    )
    matches = pattern.finditer(response_text)
    for match in matches:
        relative_path_str = match.group(1).strip().replace('\\', '/') # Normalize slashes
        language = match.group(2).strip().lower() if match.group(2) else None # Detected language tag
        code_content = match.group(3).strip()

        # Basic security check on the relative path provided by AI
        if ".." in relative_path_str:
            st.warning(f"AI proposed a path with '..', potentially unsafe: '{relative_path_str}'. Skipping this proposal.")
            continue


        relative_path_obj = Path(relative_path_str)
        absolute_path = None

        # --- Start: Determine Absolute Path Logic ---
        # Check if the relative path already includes a standard source root
        includes_standard_root = any(
            relative_path_str.startswith(str(Path(root)).replace('\\','/') + '/') for root in [ # Use Path for consistency
                 JAVA_SRC_DIRS[0], JAVA_SRC_DIRS[1], STATIC_SRC_DIR, # Added static dir
                 'src/main/resources', 'src/test/resources', # Other common resource dirs
                 relative_robot_path_str # Robot tests dir
            ]
        )

        if includes_standard_root:
             # Assume the path is correct relative to PROJECT_ROOT
            potential_path = PROJECT_ROOT / relative_path_obj
        else:
            # Guess the base directory based on extension
            ext = relative_path_obj.suffix.lower()
            guessed_base = None
            if ext == '.java':
                # Check if it looks like a test file
                if relative_path_obj.name.endswith("Test.java") or relative_path_obj.name.endswith("Tests.java"):
                     guessed_base = Path(JAVA_SRC_DIRS[1]) # src/test/java
                else:
                     guessed_base = Path(JAVA_SRC_DIRS[0]) # src/main/java
            elif ext in ['.html', '.css', '.js']:
                 guessed_base = Path(STATIC_SRC_DIR) # src/main/resources/static
            elif ext == '.robot':
                 guessed_base = Path(relative_robot_path_str) # src/test/robotframework
            elif ext in ['.xml', '.properties']:
                 # Guess main resources, could refine based on path elements if needed
                 if 'test' in relative_path_str.lower():
                      guessed_base = Path('src/test/resources')
                 else:
                      guessed_base = Path('src/main/resources')


            if guessed_base:
                potential_path = PROJECT_ROOT / guessed_base / relative_path_obj
            else:
                # Fallback if extension is unknown or path seems weird - place directly under root
                st.warning(f"Could not determine standard directory for '{relative_path_str}'. Assuming relative to project root.")
                potential_path = PROJECT_ROOT / relative_path_obj # Place in root as last resort
                if not language: # Try guessing language again if needed
                     language = get_file_language(relative_path_obj)

        # --- Security Check on final path ---
        try:
             resolved_path = potential_path.resolve()
             if resolved_path.is_relative_to(PROJECT_ROOT.resolve()):
                 absolute_path = potential_path # Assign only if safe
             else:
                 st.warning(f"AI proposed path '{relative_path_str}' resolves outside the project root. Skipping.")
                 absolute_path = None # Explicitly set to None if unsafe
        except Exception as e:
             st.warning(f"Error resolving or checking path '{potential_path}': {e}. Skipping.")
             absolute_path = None


        # --- End: Determine Absolute Path Logic ---

        # If language tag was missing, guess from file extension *of the relative path*
        if not language and absolute_path: # Guess only if path is valid
            language = get_file_language(absolute_path)

        if absolute_path: # Only add if path is valid and safe
            parsed_data.append({
                "relative_path": relative_path_str,
                "absolute_path": str(absolute_path), # Store as string
                "language": language or "plaintext", # Ensure language is never None
                "code": code_content
            })

    # Fallback if markers are missing but a code block exists (Less likely to work well for Apply Changes)
    if not parsed_data and "```" in response_text:
        code_match = re.search(r"```(java|html|css|javascript|robotframework|xml|properties|md|)?\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE)
        if code_match:
            st.warning("AI response didn't use FILE markers. Extracted first code block, but cannot determine file path reliably.")
            language = code_match.group(1).strip().lower() if code_match.group(1) else "plaintext"
            code_content = code_match.group(2).strip()
            parsed_data.append({
                "relative_path": "Unknown (AI response format error)",
                "absolute_path": None, # Cannot determine reliably
                "language": language,
                "code": code_content
            })

    return parsed_data


def write_changes_to_file(file_path_str, new_content):
    """Writes the new content to the specified file, ensuring it's within the project."""
    try:
        file_path = Path(file_path_str)
        # --- Security Check before writing ---
        resolved_path = file_path.resolve()
        if not resolved_path.is_relative_to(PROJECT_ROOT.resolve()):
             st.error(f"Security Error: Attempted to write file outside project root: {file_path}")
             return False

        # Ensure parent directory exists (handles creation)
        # Check parent directory safety as well
        parent_dir = file_path.parent
        if parent_dir.resolve().is_relative_to(PROJECT_ROOT.resolve()):
             parent_dir.mkdir(parents=True, exist_ok=True)
        else:
             st.error(f"Security Error: Attempted to create directory outside project root: {parent_dir}")
             return False

        file_path.write_text(new_content, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Error writing changes to {file_path_str}: {e}")
        return False

# --- Modified run_robot_tests function ---
def run_robot_tests(test_path, cwd):
    """
    Runs Robot Framework tests. Returns: (success_bool, full_output_str)
    """
    # Ensure test_path is a Path object and exists
    if not isinstance(test_path, Path):
        test_path = Path(test_path)

    if not test_path.exists():
         err_msg = f"Robot test path does not exist: {test_path}"
         st.error(err_msg)
         return False, f"ERROR: {err_msg}"

    # Security check on cwd
    if not Path(cwd).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        err_msg = f"Security Error: Attempting to run tests outside project root CWD: {cwd}"
        st.error(err_msg)
        return False, f"ERROR: {err_msg}"


    command = ["robot", str(test_path)]
    st.info(f"Running Robot tests: `{' '.join(command)}` in `{cwd}`")
    full_output = f"--- Robot Test Log: {' '.join(command)} ---\n\n"
    process = None
    success = False
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Combine stdout and stderr
            text=True,
            encoding='utf-8',
            errors='replace', # Handle potential decoding errors
            bufsize=1, # Line buffering
            # Security: Consider adding resource limits if needed (platform dependent)
        )

        # Read output line by line and append to full_output
        # Add a timeout mechanism to prevent hangs
        output_lines = []
        start_time = time.time()
        MAX_TEST_TIME = 300 # 5 minutes timeout for tests

        while True:
             # Check for timeout
             if time.time() - start_time > MAX_TEST_TIME:
                  st.warning(f"Robot test execution timed out after {MAX_TEST_TIME} seconds.")
                  if process.poll() is None: # If still running, try to terminate
                       process.terminate()
                       time.sleep(0.5)
                       if process.poll() is None:
                            process.kill()
                  full_output += "\n\nERROR: Test execution timed out.\n"
                  success = False
                  break # Exit the reading loop


             line = process.stdout.readline()
             if not line and process.poll() is not None: # Process finished and no more output
                 break
             if line:
                  output_lines.append(line)
                  # Optional: Add a slight delay if output is too fast for Streamlit
                  # time.sleep(0.01)

             # Brief sleep if no line to avoid busy-waiting
             if not line:
                  time.sleep(0.1)


        full_output += "".join(output_lines) # Append collected lines

        # Ensure process has finished after loop (handles cases where readline might miss EOF before poll)
        if process.poll() is None:
            process.wait(timeout=5) # Wait a bit longer


        return_code = process.returncode
        success = return_code == 0
        full_output += f"\n--- Test Execution {'Complete' if success else 'Failed'} (Exit Code: {return_code}) ---"

        return success, full_output

    except FileNotFoundError:
        err_msg = "Error: 'robot' command not found. Is Robot Framework installed and in PATH?"
        st.error(err_msg) # Show error immediately
        full_output += f"\nERROR: {err_msg}"
        return False, full_output
    except subprocess.TimeoutExpired:
         st.error("Robot test process timed out waiting for completion after output.")
         full_output += "\n\nERROR: Process timed out after output reading."
         return False, full_output
    except Exception as e:
        err_msg = f"An error occurred while running Robot tests: {e}"
        st.error(err_msg) # Show error immediately
        full_output += f"\nERROR: {err_msg}"
        return False, full_output
    finally:
        # Ensure process is properly closed if it exists and is still running
        if process and process.poll() is None:
            try:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
            except Exception as kill_e:
                st.warning(f"Error terminating robot process: {kill_e}")


# --- Functions for Running Processes (check_port, run_command_separate_terminal) ---
def check_port(host="127.0.0.1", port=8081, retries=30, delay=2): #<-- Adjusted default port
    """Checks if a port is open and accepting connections."""
    st.write(f"Checking if port {host}:{port} is open...") # Verbose output
    for i in range(retries):
        try:
            with socket.create_connection((host, port), timeout=1):
                st.write(f"Port {port} check {i+1}/{retries}: Connected!")
                return True
        except socket.timeout:
            # st.write(f"Port {port} check {i+1}/{retries}: Timeout") # Can be noisy
            pass
        except ConnectionRefusedError:
            # st.write(f"Port {port} check {i+1}/{retries}: Connection refused") # Can be noisy
            pass
        except Exception as e:
            st.warning(f"Port check {i+1}/{retries} encountered error: {e}")
            # Fall through to sleep
        if i < retries -1 : # Only sleep if not the last retry
             time.sleep(delay)
    st.write(f"Port {port} check failed after {retries} retries.")
    return False

def run_command_separate_terminal(command_list, cwd):
    """Tries to run a command in a new terminal window."""
    # Security Check on CWD
    if not Path(cwd).resolve().is_relative_to(PROJECT_ROOT.resolve()):
        st.error(f"Security Error: Attempting to run command outside project root CWD: {cwd}")
        return False

    system = platform.system()
    st.write(f"Attempting to run `{' '.join(command_list)}` in new terminal (OS: {system}, CWD: {cwd})")
    try:
        if system == "Windows":
            # Use start cmd /k to keep window open after command finishes
            # Ensure command parts are handled reasonably by cmd (might need more robust quoting for complex args)
            # Using shell=True is inherently risky if command_list parts came from untrusted sources.
            # We assume command_list here is constructed internally (like 'mvn spring-boot:run')
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", " ".join(command_list)], cwd=cwd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True
        elif system == "Darwin": # macOS
            # More robust quoting for cwd and command
            cwd_escaped = shlex.quote(str(cwd))
            # Join the command list into a single string THEN quote the whole thing for osascript
            # This assumes the command itself doesn't need complex internal quoting for the shell inside the terminal
            cmd_string = " ".join(command_list)
            # Further escape for AppleScript string literal
            cmd_escaped_applescript = cmd_string.replace('\\', '\\\\').replace('"', '\\"')

            script = f'tell application "Terminal" to do script "cd {cwd_escaped} && {cmd_escaped_applescript}" activate'

            proc = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=10) # Add timeout
            if proc.returncode != 0:
                st.error(f"osascript failed: {stderr.decode(errors='replace')}")
                return False
            return True
        elif system == "Linux":
            # Need shlex for proper quoting
            quoted_cmd_list = [shlex.quote(part) for part in command_list]
            quoted_cwd = shlex.quote(str(cwd))
            cmd_string_linux = " ".join(quoted_cmd_list)

            terminals = [
                 # Use -- working directory where possible
                {"cmd": ["gnome-terminal", "--working-directory", str(cwd), "--"] + command_list},
                {"cmd": ["konsole", "--workdir", str(cwd), "-e"] + command_list},
                # xterm needs careful quoting and a way to keep open
                {"cmd": ["xterm", "-hold", "-e", f"sh -c 'cd {quoted_cwd} && {cmd_string_linux}'"]}, # Wrap in sh -c
                # Add other common terminals if needed (e.g., terminator, tilix)
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
                    # st.write(f"Terminal '{term_cmd[0]}' not found.") # Can be noisy
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
        return False
    except Exception as e:
        st.error(f"Failed to start command in new terminal: {e}")
        return False

# --- Streamlit App UI and Logic ---

st.set_page_config(page_title="Code Assistant", layout="wide")
st.title("🤖 Tech-AI Agent")
st.success("Gemini - gemini-1.5-pro-latest AI initialised")
#st.markdown(f"**Project Root:** `{PROJECT_ROOT}`")
# Display Robot path only if it was found and is a directory
if 'full_robot_path' in locals() and isinstance(full_robot_path, Path) and full_robot_path.is_dir():
    st.markdown(f"")
else:
    st.markdown(f"**Robot Tests:** *(Path not configured or found)*")

st.markdown("""
* Ask AI to analyze, modify, or **create** Java, HTML, CSS, JS, Robot, XML, etc. code.
* Specify file names (e.g., `MyService.java`, `task.html`, `tests.robot`). **Use relative paths for clarity.**
* Type `run myapp` to start Spring Boot app & run Robot tests (if configured). Git operations run if tests pass.
* **Apply Changes:** Use button below code proposals (**CAUTION: Overwrites/Creates files!**).
* **`run myapp` Note:** Starts app in a **new terminal**. **Stop it manually** (close window / Ctrl+C). Test & Git logs appear below.
""")

# Initialize Gemini Model and Chat History
def init_gemini():
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        st.session_state.gemini_model = model
        st.session_state.chat = model.start_chat(history=[])
        st.session_state.init_error = None
    except Exception as e:
        st.error(f"Fatal Error: Failed to initialize Gemini model: {e}")
        st.session_state.init_error = e
        st.stop() # Stop execution if model fails to init


# Initialize state only if not already done or if model needs re-init
if "gemini_model" not in st.session_state or "chat" not in st.session_state:
    init_gemini()

# Initialize other session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "proposed_changes" not in st.session_state:
    st.session_state.proposed_changes = None # Stores the dict for the *single* latest proposal
if "run_process_pid" not in st.session_state:
    st.session_state.run_process_pid = None # To track external process if needed (though we run in sep terminal)


# Check for initialization errors on rerun
if st.session_state.get("init_error"):
     st.error(f"Gemini model initialization failed previously: {st.session_state.init_error}")
     st.stop()


# --- Display Chat History ---
# Display messages from history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # Display regular message content
        st.markdown(message["content"])

        # Check if this assistant message has code proposals
        proposals = message.get("code_proposals", [])  # Changed from code_proposal to code_proposals (list)
        if message["role"] == "assistant" and proposals:
            # Display each proposal with its own Apply button
            for proposal in proposals:
                # Display code block
                st.code(proposal["code"], language=proposal.get("language", "plaintext"))
                path_display = proposal.get('relative_path', 'Unknown Path')

                if path_display == "Unknown (AI response format error)":
                    st.text("")
                else:
                    st.caption(f"Suggested code for: `{path_display}`")

                    # Show Apply button if this is the latest message
                    if i == len(st.session_state.messages) - 1:
                        abs_path = proposal.get("absolute_path")

                        if abs_path:
                            try:
                                file_exists = Path(abs_path).exists()
                                action_label = "Create" if not file_exists else "Apply to"
                                button_label = f"{action_label} `{proposal['relative_path']}`"
                                # Unique key using message index, path hash, and proposal index
                                button_key = f"apply_button_{i}_{hash(abs_path)}_{hash(proposal['code'])}"

                                if st.button(button_label, key=button_key, type="primary"):
                                    with st.spinner(f"{action_label} `{proposal['relative_path']}`..."):
                                        success = write_changes_to_file(abs_path, proposal["code"])

                                    if success:
                                        result_verb = "created" if not file_exists else "applied"
                                        st.success(f"Changes successfully {result_verb}!")
                                        time.sleep(1)
                                        st.rerun()

                            except Exception as button_exc:
                                st.error(f"Error handling file {abs_path}: {button_exc}")
                        else:
                            st.error("Cannot determine safe file path for this code. Cannot apply changes.")

# --- Chat Input and Processing ---
if prompt := st.chat_input("Ask AI, or type 'run myapp'"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- SPECIAL COMMAND: run myapp ---
    if prompt.strip().lower() == "run myapp":
        st.session_state.proposed_changes = None # Clear any pending proposals
        # Add messages to history as things happen
        # Use a single assistant message block for the whole sequence
        with st.chat_message("assistant"):
            status_placeholder = st.empty() # Placeholder for status updates
            git_status_placeholder = st.empty() # Placeholder specifically for git status

            run_summary_md = "### MyApp Execution Sequence\n\n" # Start summary

            # 1. Start Spring Boot
            status_placeholder.info("Attempting to start Spring Boot app (`mvn spring-boot:run`) in a new terminal...")
            started = run_command_separate_terminal(["mvn", "spring-boot:run", "-Dserver.port=8081"], cwd=PROJECT_ROOT_PATH) # Specify port

            if not started:
                status_placeholder.error("Failed to start Spring Boot app. Check console/try manually.")
                run_summary_md += "* ❌ Failed to start Spring Boot app in a new terminal.\n"
                # Append error message and stop 'run myapp' sequence here
                st.session_state.messages.append({"role": "assistant", "content": run_summary_md})
                st.rerun() # Rerun to show the failure message
            else:
                run_summary_md += "* ✅ Spring Boot app likely started in new terminal (check for it!). **Remember to stop it manually.**\n"
                port_to_check = 8081 # Match the port in mvn command
                status_placeholder.info(f"Waiting for port {port_to_check} to become active (up to 60s)...")
                run_summary_md += f"* ⏳ Waiting for port {port_to_check}...\n"
                # Update display immediately
                status_placeholder.markdown(run_summary_md)

                # 2. Check Port
                port_active = check_port(port=port_to_check, retries=30, delay=2) # Check correct port

                if port_active:
                    status_placeholder.success(f"Port {port_to_check} active!")
                    run_summary_md += f"* ✅ Port {port_to_check} is active.\n"
                    status_placeholder.markdown(run_summary_md) # Update summary

                    # 3. Run Robot Tests (Check if path exists and is configured)
                    robot_path_valid = 'full_robot_path' in locals() and isinstance(full_robot_path, Path) and full_robot_path.is_dir()

                    if not robot_path_valid:
                        status_placeholder.warning(f"Cannot run Robot tests: Path not configured or found. Skipping tests and Git operations.")
                        run_summary_md += f"* ⚠️ Warning: Robot test path not configured or found, skipping tests & Git.\n"
                        tests_succeeded = False # Mark as failed to skip git
                    else:
                        run_summary_md += "* ▶️ Running Robot Framework tests...\n"
                        status_placeholder.info("Running Robot Framework tests...") # Update status area
                        status_placeholder.markdown(run_summary_md) # Update summary display

                        # Run tests and get logs
                        tests_succeeded, robot_output = run_robot_tests(full_robot_path, PROJECT_ROOT_PATH)

                        # Add Robot log message to history immediately
                        log_status = "Success" if tests_succeeded else "Failure"
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "robot_log",
                            "content": f"Robot Test Run: {log_status}\n\n{robot_output}" # Add status to content
                        })

                        if tests_succeeded:
                            run_summary_md += "* ✅ Robot tests completed successfully.\n"
                            status_placeholder.success("Robot tests passed!")
                        else:
                            run_summary_md += "* ❌ Robot tests failed.\n"
                            status_placeholder.error("Robot tests failed.")
                            # tests_succeeded is already False

                    # 4. Run Git Operations (only if tests succeeded or were skipped due to config but app started)
                    # We only run git if tests_succeeded is True
                    if tests_succeeded:
                        run_summary_md += "* ▶️ Running Git operations (add, commit, push)...\n"
                        status_placeholder.info("Running Git operations...") # Update status area
                        status_placeholder.markdown(run_summary_md) # Update summary display
                        result = git_operations.execute_git_flow(PROJECT_ROOT, GIT_COMMIT_MESSAGE, "")
                    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], str):
                        run_summary_md += result[1]
                        if git_operations.deploy_to_heroku_separate_terminal(PROJECT_ROOT):
                            st.success(f"Attempted to deploy to Heroku from a new terminal in: {PROJECT_ROOT}")
                        else:
                            st.error(f"Failed to open a new terminal to deploy to Heroku from: {PROJECT_ROOT}")

                    else:
                        # Handle the case where the return is not the expected tuple
                        print(f"Warning: execute_git_flow returned unexpected type or format: {type(result)}, value: {result}")
                        # You might want to assign an empty string or handle this differently
                        pass
                    
                        
                        # Create a placeholder for git status updates
                        git_status_placeholder = st.empty()
                        
                        # Ensure we have a valid placeholder
                        if git_status_placeholder:
                            try:
                                # Create a container for git operations
                                with st.container() as git_container:
                                    if git_container:
                                        st.info(f"Attempting git operations in directory: {PROJECT_ROOT}")
                                        
                                        # Initialize git operations
                                        git_success = True
                                        git_output = ""
                                        
                                        # Before running git commands, check configuration
                                        git_config_ok, git_config_msg = git_operations.execute_git_flow(PROJECT_ROOT, GIT_COMMIT_MESSAGE, "")
                                        if not git_config_ok:
                                            git_status_placeholder.error(f"Git configuration error: {git_config_msg}")
                                            run_summary_md += f"* ❌ Git operations failed: {git_config_msg}\n"
                                            status_placeholder.error("Git configuration error.")
                                        else:
                                            # Initialize git operations
                                            git_success = True
                                            git_output = ""
                                            
                                            # 1. Git Status (check for changes)
                                            status_output, status_success = git_operations.run_git_command(
                                                ["git", "status"], PROJECT_ROOT, git_status_placeholder
                                            )
                                            git_output += status_output
                                            
                                            if "nothing to commit" in status_output:
                                                git_status_placeholder.info("No changes to commit")
                                                run_summary_md += "* ℹ️ No changes to commit\n"
                                            else:
                                                # 2. Git Add
                                                add_output, add_success = git_operations.run_git_command(
                                                    ["git", "add", "."], PROJECT_ROOT, git_status_placeholder
                                                )
                                                git_output += "\n" + add_output
                                                git_success = git_success and add_success
                                                
                                                if add_success:
                                                    # 3. Git Commit
                                                    commit_output, commit_success = git_operations.run_git_command(
                                                        ["git", "commit", "-m", GIT_COMMIT_MESSAGE], PROJECT_ROOT, git_status_placeholder
                                                    )
                                                    git_output += "\n" + commit_output
                                                    git_success = git_success and commit_success
                                                    
                                                    if commit_success:
                                                        # 4. Git Pull before Push (to avoid conflicts)
                                                        pull_output, pull_success = git_operations.run_git_command(
                                                            ["git", "pull", "origin", "main"], PROJECT_ROOT, git_status_placeholder
                                                        )
                                                        git_output += "\n" + pull_output
                                                        
                                                        # 5. Git Push
                                                        push_output, push_success = git_operations.run_git_command(
                                                            ["git", "push", "origin", "main"], PROJECT_ROOT, git_status_placeholder
                                                        )
                                                        git_output += "\n" + push_output
                                                        git_success = git_success and push_success

                                            # Display results
                                            if git_success:
                                                git_status_placeholder.success("✅ All git operations completed successfully!")
                                                run_summary_md += "* ✅ Git operations completed successfully.\n"
                                                status_placeholder.success("Git operations completed.")
                                            else:
                                                git_status_placeholder.error("❌ One or more git operations failed.")
                                                run_summary_md += "* ❌ Git operations failed.\n"
                                                status_placeholder.error("Git operations failed.")
                                            
                                            # Show detailed output
                                            git_status_placeholder.markdown(f"```\n{git_output}\n```")
                                        
                            except Exception as e:
                                git_status_placeholder.error(f"❌ Error during git operations: {str(e)}")
                                run_summary_md += f"* ❌ Git operations failed: {str(e)}\n"
                                status_placeholder.error("Git operations failed.")
                                git_success = False
                        elif robot_path_valid: # Only add skip message if tests were actually run and failed
                            run_summary_md += "* ⏭️ Skipping Git operations due to failed tests.\n"
                            status_placeholder.warning("Skipping Git operations due to failed tests.")


                else: # Port not active
                    status_placeholder.error(f"Port {port_to_check} did not become active. Check application terminal. Skipping tests & Git.")
                    run_summary_md += f"* ❌ Error: Port {port_to_check} did not become active. Skipping tests & Git.\n"

            # Append the final summary message AFTER logs have been added
            st.session_state.messages.append({"role": "assistant", "content": run_summary_md})
            # Clear placeholders at the end
            status_placeholder.empty()
            git_status_placeholder.empty()
            st.rerun() # Rerun to display all new messages


    # --- REGULAR AI PROCESSING ---
    else:
        # Add assistant thinking message
        with st.chat_message("assistant"):
            # ***** CORRECTION: Initialize placeholder safely *****
            message_placeholder = st.empty()
            thinking_status = None # Initialize status variable
            full_response_text = ""
            st.session_state.proposed_changes = None # Clear previous proposal before new request
            assistant_message = {"role": "assistant", "content": "...", "code_proposals": []} # Default message

            try:
                # Indicate thinking right away
                thinking_status = message_placeholder.status("Thinking...", expanded=False)

                # --- Find Files Mentioned in Prompt for Context ---
                # Use a more robust regex to find potential file paths or names
                potential_files_matches = re.findall(
                    r'([\w./-]+\.(?:java|html|css|js|robot|xml|properties|md))|' # Paths with extensions
                    r'(\b[A-Z]\w*Service\b|\b[A-Z]\w*Controller\b|\b[A-Z]\w*Repository\b|\b[A-Z]\w*Entity\b|\b[A-Z]\w*Application\b)|' # Java patterns
                    r'(\btask\.html\b|\bindex\.html\b|\bstyles?\.css\b|\bscript[s]?\.js\b|\btests?\.robot\b|\bpom\.xml\b)', # Specific common names + task.html
                    prompt, re.IGNORECASE # Ignore case for filenames
                )
                # Flatten the list of tuples from findall
                flat_potential_files = {item for sublist in potential_files_matches for item in sublist if item} # Use set for uniqueness


                file_context_for_prompt = ""
                MAX_CONTEXT_FILES = 3
                files_processed_for_context = 0

                if flat_potential_files:
                    with thinking_status if thinking_status else message_placeholder.expander("File Context Search", expanded=False) as context_container:
                         # Check if context_container is valid before writing
                         if hasattr(context_container, 'write'):
                             context_container.write(f"Detected potential file mentions: {', '.join(flat_potential_files)}")
                             for file_to_search in flat_potential_files:
                                 if files_processed_for_context >= MAX_CONTEXT_FILES:
                                     context_container.write("Skipping further file reads (max context limit reached).")
                                     break

                                 context_container.write(f"Searching for '{file_to_search}'...")
                                 found_path_obj = find_project_file(file_to_search)

                                 if found_path_obj:
                                     context_container.write(f"Reading '{found_path_obj.relative_to(PROJECT_ROOT)}'...")
                                     content = read_file_content(found_path_obj) # Already checks security
                                     if content is not None:
                                         # Prepare context string (limit size if needed)
                                         MAX_FILE_SIZE_CONTEXT = 5000 # Limit context size per file
                                         if len(content) > MAX_FILE_SIZE_CONTEXT:
                                              content = content[:MAX_FILE_SIZE_CONTEXT] + "\n... [File Content Truncated] ..."
                                              context_container.warning(f"Content truncated for '{file_to_search}'.")


                                         relative_p = str(found_path_obj.relative_to(PROJECT_ROOT)).replace('\\', '/')
                                         lang = get_file_language(found_path_obj)
                                         file_context_for_prompt += f"\n--- START CONTEXT FILE: {relative_p} ---\n"
                                         file_context_for_prompt += f"```{lang}\n{content}\n```\n"
                                         file_context_for_prompt += f"--- END CONTEXT FILE: {relative_p} ---\n"
                                         context_container.write(f"Added context from '{relative_p}'.")
                                         files_processed_for_context += 1
                                     else:
                                          context_container.warning(f"Found '{file_to_search}' but could not read it.")
                                 else:
                                     context_container.info(f"Could not find existing file matching '{file_to_search}'.")
                         else:
                              st.warning("Could not display file context search details.")


                # --- Construct the prompt for Gemini ---
                # This prompt structure asks the AI to determine the path, fulfilling the user's request.
                ai_prompt = f"""You are an expert AI developer assistant skilled in Java/Spring Boot, HTML, CSS, JavaScript, Robot Framework, XML, and general project structure for a project typically using Maven/Gradle.
Project Root (for context, do not use this exact path in output): {PROJECT_ROOT_PATH}

Standard Source Directories (use these relative paths in your output):
- Java Source: {JAVA_SRC_DIRS[0]} (Main), {JAVA_SRC_DIRS[1]} (Test)
- Static Web Assets (HTML/CSS/JS): {STATIC_SRC_DIR}
- Robot Tests: {relative_robot_path_str}
- Maven/Gradle Config: usually pom.xml or build.gradle at the root
- Resources: src/main/resources, src/test/resources

User Request:
{prompt}

{f"Relevant File Context Provided by User (Paths relative to Project Root):\n{file_context_for_prompt}" if file_context_for_prompt else "No specific file context provided. Analyze the request based on general knowledge and the user prompt."}

Instructions:
1. Analyze the user request carefully. Understand if they want to analyze, modify, **create**, or explain code/concepts.
2. If the user asks to modify or create code/files:
   a. Provide the **complete code** for the relevant file(s).
   b. **Determine the correct relative path** from the project root based on standard conventions (e.g., Java classes go into `{JAVA_SRC_DIRS[0]}/<package>`, HTML/CSS/JS into `{STATIC_SRC_DIR}`, Robot tests into `{relative_robot_path_str}`, etc.) or user specification if valid.
   c. **CRUCIAL FORMATTING:** Format the code output EXACTLY like this:
      --- START FILE: path/relative/to/project/root/FileName.ext ---
      ```language_tag
      // COMPLETE new or modified code for the file goes here
      ```
      --- END FILE: path/relative/to/project/root/FileName.ext ---
   d. Use the correct language tag (java, html, css, javascript, robotframework, xml, properties, md, etc.).
   e. Provide the complete file content, not just snippets, unless specifically asked for a snippet.
   f. If creating a new file, infer the path based on standard practices for the file type unless the user specified a valid relative path. For example, a new HTML file like 'task.html' usually belongs in `{STATIC_SRC_DIR}`.
3. If the request is conceptual or doesn't require code changes (e.g., "explain this concept"), answer directly without using the file markers or code blocks, unless generating a generic example.
4. Ensure code is well-formatted and follows common best practices for the language.

Please provide your analysis, explanation, modified code, or new code based on the user's request:
"""

                # Send prompt to Gemini
                # Update status before sending
                if thinking_status: thinking_status.update(label="Sending request to Gemini AI...")

                response = st.session_state.chat.send_message(ai_prompt, stream=True)

                # Stream the response
                stream_successful = False
                # Update status while streaming
                if thinking_status: thinking_status.update(label="Receiving Gemini AI response...")

                response_chunks = []
                for chunk in response:
                    # Check for immediate blocking feedback (might be in the first chunk)
                    if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback.block_reason:
                        st.error(f"Response blocked by safety settings: {chunk.prompt_feedback.block_reason}")
                        full_response_text = f"Error: Response blocked by safety settings ({chunk.prompt_feedback.block_reason})."
                        response_chunks = [full_response_text] # Set final text
                        stream_successful = False
                        break # Stop processing this response

                    # Append text and update placeholder
                    chunk_text = chunk.text
                    response_chunks.append(chunk_text)
                    full_response_text = "".join(response_chunks) # Rebuild full text each time
                    # ***** CORRECTION: Check placeholder before writing *****
                    if message_placeholder:
                         message_placeholder.markdown(full_response_text + "▌") # Use cursor indicator
                    stream_successful = True


                if not stream_successful and not full_response_text : # Handle case where stream failed early
                     full_response_text = "Error: Failed to get response stream from AI."
                     if message_placeholder: message_placeholder.error(full_response_text)


                # Display final complete response without cursor
                if message_placeholder: message_placeholder.markdown(full_response_text)
                # Update status to complete
                if thinking_status: thinking_status.update(label="AI Response Received", state="complete", expanded=False)


                # --- Process Final Response ---
                if "Error: Response blocked" in full_response_text:
                    assistant_message = {"role": "assistant", "content": full_response_text, "code_proposals": []}
                else:
                    # Parse the final response for code blocks AND determine paths
                    parsed_proposals = parse_gemini_response(full_response_text)
                    # Basic message contains the full text regardless of proposals
                    assistant_message = {"role": "assistant", "content": full_response_text}

                    if parsed_proposals:
                        # Store all proposals in the message
                        assistant_message["code_proposals"] = parsed_proposals
                        # Show info about number of changes
                        st.info(f"Found {len(parsed_proposals)} code proposals. Use the buttons below each code block to apply changes.")
                    else:
                        # No proposals found or parsed
                        assistant_message["code_proposals"] = []
                        st.warning("No code proposals found in the AI response.")


            except Exception as e:
                # ***** CORRECTION: Safer error handling *****
                error_message = f"An error occurred during AI processing: {e}"
                st.error(error_message)
                full_response_text = f"Sorry, I encountered an error during processing. Please check the logs or try again.\nDetails: {e}"
                # Update placeholder safely if it exists
                if message_placeholder: message_placeholder.markdown(full_response_text)
                # Ensure status is marked as error if it exists
                if thinking_status: thinking_status.update(label="Processing Error", state="error", expanded=True)
                # Set assistant message to the error
                assistant_message = {"role": "assistant", "content": full_response_text, "code_proposals": []}


            # Add assistant response to chat history
            st.session_state.messages.append(assistant_message)
            st.rerun() # Rerun to display the new message and potentially the Apply button correctly
