import streamlit as st
from git import Repo, GitCommandError
import os
import datetime
import chardet

# --- CONFIG ---
REPO_PATH = "E:/ERP/dev/CursorAI2/myautodev"
BRANCH = "main"
LOG_FILE = "revert_log.txt"  # Simple local text file to track actions

# --- Init Git Repo ---
try:
    repo = Repo(REPO_PATH)
    assert not repo.bare
    commits = list(repo.iter_commits(BRANCH, max_count=20))
except Exception as e:
    st.error(f"Git repo error: {e}")
    st.stop()

st.set_page_config(page_title="Git Revert Dashboard", layout="wide")
st.title("🧠 Git Revert Dashboard")

# --- UTIL FUNCTIONS ---

def write_log(message: str):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a", encoding="utf-8") as f:  # 💥 fix is here
        f.write(f"[{timestamp}] {message}\n")

def revert_commit(commit_hexsha, tag_name=None):
    try:
        repo.git.revert(commit_hexsha, no_edit=True)
        commit_msg = f"Revert commit {commit_hexsha}"
        repo.index.commit(commit_msg)

        result = f"✅ Reverted commit {commit_hexsha[:7]}"

        if tag_name:
            repo.create_tag(tag_name)
            result += f"\n🏷️ Tagged as `{tag_name}`"

        origin = repo.remote(name="origin")
        origin.push()
        if tag_name:
            origin.push(tag_name)

        write_log(f"{result}")
        return result
    except GitCommandError as e:
        err = f"❌ Revert error: {str(e)}"
        write_log(err)
        return err

def get_commit_diff_preview(commit):
    parent = commit.parents[0] if commit.parents else None
    if not parent:
        return "This is the initial commit—no parent to diff."
    diff = parent.diff(commit, create_patch=True)
    preview = ""
    for d in diff:
        try:
            preview += d.diff.decode("utf-8", errors="ignore") + "\n"
        except:
            continue
    return preview if preview else "No diff found."

# --- UI Sections ---

# SIDEBAR
st.sidebar.header("🔧 Options")
view_mode = st.sidebar.radio("Choose view", ["Revert Commits", "Rollback Log"])

if view_mode == "Revert Commits":
    st.subheader("🔁 Commit List (with Revert & Preview)")
for commit in commits:
    st.markdown("---")
    with st.expander(f"{commit.hexsha[:7]} - {commit.message.strip()[:50]}"):
        st.markdown(f"""
**Commit ID:** `{commit.hexsha}`  
**Author:** {commit.author.name}  
**Date:** {commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}  
**Message:** {commit.message.strip()}  
""")

        # Inline dry-run preview toggle
        if st.checkbox(f"🧪 Show Dry-run Diff for {commit.hexsha[:7]}", key=f"preview_{commit.hexsha}"):
            st.code(get_commit_diff_preview(commit), language="diff")

        # Tag input
        version_tag = st.text_input("Optional: Tag this revert (e.g., v1.2.3-revert)", key=f"tag_{commit.hexsha}")

        # Confirmation checkbox
        confirm = st.checkbox("✅ Confirm revert", key=f"confirm_{commit.hexsha}")

        if st.button("🔄 Revert This Commit", key=commit.hexsha):
            if confirm:
                with st.spinner("Reverting commit..."):
                    result = revert_commit(commit.hexsha, version_tag if version_tag else None)
                st.success(result)
            else:
                st.warning("Please confirm the revert checkbox before continuing.")

            # Dry-run preview
            with st.expander("🧪 Dry-run Preview (Diff)"):
                st.code(get_commit_diff_preview(commit), language="diff")

            # Tag input
            version_tag = st.text_input("Optional: Tag this revert (e.g., v1.2.3-revert)", key=f"tag_{commit.hexsha}")

            # Confirmation checkbox
            confirm = st.checkbox("✅ Confirm revert", key=f"confirm_{commit.hexsha}")

            if st.button("🔄 Revert This Commit", key=commit.hexsha):
                if confirm:
                    with st.spinner("Reverting commit..."):
                        result = revert_commit(commit.hexsha, version_tag if version_tag else None)
                    st.success(result)
                else:
                    st.warning("Please confirm the revert checkbox before continuing.")

            elif view_mode == "Rollback Log":
              st.subheader("📜 Revert / Rollback History")
    if os.path.exists(LOG_FILE):
        
        
        
        with open(LOG_FILE, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result['encoding']
        with open(LOG_FILE, 'r', encoding=encoding) as f:
            logs = f.readlines()   
            
        for log in reversed(logs[-100:]):
            st.markdown(f"- {log.strip()}")
    else:
        st.info("No revert actions have been logged yet.")
