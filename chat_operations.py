import streamlit as st
from config import *
from file_operations import find_project_file, read_file_content, get_file_language
from gemini_operations import parse_gemini_response
import git_operations
from process_operations import check_port, run_command_separate_terminal, run_robot_tests
import re

def process_chat_message(message, index=None):
    """Process and display chat message with code proposals"""
    proposals = message.get("code_proposals", [])
    if message["role"] == "assistant" and proposals:
        for proposal in proposals:
            st.code(proposal["code"], language=proposal.get("language", "plaintext"))
            path_display = proposal.get('relative_path', 'Unknown Path')

            if path_display != "Unknown (AI response format error)":
                st.caption(f"Suggested code for: `{path_display}`")
                if index == len(st.session_state.messages) - 1:
                    handle_code_proposal(proposal, path_display)

def handle_code_proposal(proposal, path_display):
    """Handle the code proposal UI and actions"""
    abs_path = proposal.get("absolute_path")
    if abs_path:
        try:
            file_exists = Path(abs_path).exists()
            action_label = "Create" if not file_exists else "Apply to"
            button_label = f"{action_label} `{proposal['relative_path']}`"
            button_key = f"apply_button_{hash(abs_path)}_{hash(proposal['code'])}"

            if st.button(button_label, key=button_key, type="primary"):
                with st.spinner(f"{action_label} `{proposal['relative_path']}`..."):
                    success = write_changes_to_file(abs_path, proposal["code"])
                if success:
                    result_verb = "created" if not file_exists else "applied"
                    st.success(f"Changes successfully {result_verb}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error handling file {abs_path}: {e}")
    else:
        st.error("Cannot determine safe file path for this code. Cannot apply changes.")

def handle_run_myapp():
    """Handle the 'run myapp' command sequence"""
    st.session_state.proposed_changes = None
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        git_status_placeholder = st.empty()
        run_summary_md = "### MyApp Execution Sequence\n\n"

        # Start Spring Boot
        if not start_spring_boot(status_placeholder, run_summary_md):
            return

        # Check port and run tests
        if check_port_and_run_tests(status_placeholder, run_summary_md):
            # Run Git operations if tests passed
            run_git_operations(status_placeholder, run_summary_md)

        # Append final summary and clean up
        st.session_state.messages.append({"role": "assistant", "content": run_summary_md})
        status_placeholder.empty()
        git_status_placeholder.empty()
        st.rerun()

def start_spring_boot(status_placeholder, run_summary_md):
    """Start Spring Boot application"""
    status_placeholder.info("Attempting to start Spring Boot app (`mvn spring-boot:run`) in a new terminal...")
    started = run_command_separate_terminal(
        ["mvn", "spring-boot:run", "-Dserver.port=8081"],
        cwd=PROJECT_ROOT_PATH
    )
    
    if not started:
        status_placeholder.error("Failed to start Spring Boot app. Check console/try manually.")
        run_summary_md += "* ❌ Failed to start Spring Boot app in a new terminal.\n"
        st.session_state.messages.append({"role": "assistant", "content": run_summary_md})
        st.rerun()
        return False
    return True

def check_port_and_run_tests(status_placeholder, run_summary_md):
    """Check port activity and run tests if port is active"""
    port_to_check = 8081
    if not wait_for_port(port_to_check, status_placeholder, run_summary_md):
        return False

    robot_path_valid = 'full_robot_path' in globals() and isinstance(full_robot_path, Path) and full_robot_path.is_dir()
    if not robot_path_valid:
        status_placeholder.warning("Cannot run Robot tests: Path not configured or found.")
        run_summary_md += "* ⚠️ Warning: Robot test path not configured or found, skipping tests & Git.\n"
        return False

    run_summary_md += "* ▶️ Running Robot Framework tests...\n"
    status_placeholder.info("Running Robot Framework tests...")
    status_placeholder.markdown(run_summary_md)

    tests_succeeded, robot_output = run_robot_tests(full_robot_path, PROJECT_ROOT_PATH)
    st.session_state.messages.append({
        "role": "assistant",
        "type": "robot_log",
        "content": f"Robot Test Run: {'Success' if tests_succeeded else 'Failure'}\n\n{robot_output}"
    })

    update_test_status(tests_succeeded, status_placeholder, run_summary_md)
    return tests_succeeded

def wait_for_port(port, status_placeholder, run_summary_md):
    """Wait for port to become active"""
    status_placeholder.info(f"Waiting for port {port} to become active (up to 60s)...")
    run_summary_md += f"* ⏳ Waiting for port {port}...\n"
    status_placeholder.markdown(run_summary_md)
    
    port_active = check_port(port=port, retries=30, delay=2)
    if not port_active:
        status_placeholder.error(f"Port {port} did not become active.")
        run_summary_md += f"* ❌ Error: Port {port} did not become active. Skipping tests & Git.\n"
        return False
    return True

def update_test_status(tests_succeeded, status_placeholder, run_summary_md):
    """Update test status in UI and summary"""
    if tests_succeeded:
        run_summary_md += "* ✅ Robot tests completed successfully.\n"
        status_placeholder.success("Robot tests passed!")
    else:
        run_summary_md += "* ❌ Robot tests failed.\n"
        status_placeholder.error("Robot tests failed.")

def run_git_operations(status_placeholder, run_summary_md):
    """Execute Git operations"""
    run_summary_md += "* ▶️ Running Git operations (add, commit, push)...\n"
    status_placeholder.info("Running Git operations...")
    status_placeholder.markdown(run_summary_md)
    
    result = git_operations.execute_git_flow(PROJECT_ROOT, GIT_COMMIT_MESSAGE, "")
    if isinstance(result, tuple) and len(result) == 2:
        success, message = result
        run_summary_md += message
        
        if success and git_operations.deploy_to_heroku_separate_terminal(PROJECT_ROOT):
            run_summary_md += "* ✅ Initiated Heroku deployment from new terminal\n"
        else:
            run_summary_md += "* ❌ Failed to initiate Heroku deployment\n"
    else:
        run_summary_md += "* ❌ Git operations returned unexpected result\n"
        st.error(f"Git operations returned unexpected format: {result}")