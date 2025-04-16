import streamlit as st
from git import Repo, GitCommandError
import os
import datetime
import chardet

# --- CONFIG ---
REPO_PATH = "E:/ERP/dev/CursorAI2/myautodev"
BRANCH = "main"
LOG_FILE = "revert_log.txt"

# --- Init Git Repo ---
try:
    repo = Repo(REPO_PATH)
    assert not repo.bare
    commits = list(repo.iter_commits(BRANCH, max_count=20))
except Exception as e:
    st.error(f"Git repo error: {e}")
    st.stop()

st.set_page_config(page_title="Git Revert Dashboard", layout="wide")
st.title("🤖 Git Revert Dashboard with AI Agent")

# --- UTIL FUNCTIONS ---

def write_log(message: str):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def revert_commit(commit_hexsha, tag_name=None):
    try:
        repo.git.revert(commit_hexsha, no_edit=True)
        commit_msg = f"Revert commit {commit_hexsha}"
        repo.index.commit(commit_msg)

        result = f"✅ Reverted commit {commit_hexsha[:7]}"

        if tag_name:
            repo.create_tag(tag_name)
            result += f"\n🏷️ Tagged as {tag_name}"

        origin = repo.remote(name="origin")
        origin.push()
        if tag_name:
            origin.push(tag_name)

        write_log(result)
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

def list_commits():
    commit_list = []
    for commit in commits:
        short_sha = commit.hexsha[:7]
        msg = commit.message.strip().split("\n")[0]
        author = commit.author.name
        date = commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')
        commit_list.append(f"🔸 `{short_sha}` - {msg} by *{author}* on {date}")
    return commit_list

def show_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result['encoding']

        with open(LOG_FILE, 'r', encoding=encoding) as f:
            return f.readlines()[-50:]
    else:
        return ["No revert logs found."]

# --- AI Chat Agent UI ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.subheader("💬 Ask Me Anything About Git Reverts")

for role, msg in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(msg)

user_input = st.chat_input("Ask something like 'show commits', 'revert abc123', 'show log'...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    response = ""

    # Commands
    if "commit" in user_input.lower():
        response = "\n".join(list_commits())
    elif "log" in user_input.lower() or "history" in user_input.lower():
        response = "\n".join([f"- {log.strip()}" for log in show_logs()])
    elif "revert" in user_input.lower():
        # Extract commit ID
        words = user_input.strip().split()
        commit_id = next((word for word in words if len(word) >= 6 and all(c in "0123456789abcdef" for c in word.lower())), None)
        if commit_id:
            # Find full hash from list
            target_commit = next((c for c in commits if c.hexsha.startswith(commit_id)), None)
            if target_commit:
                response = revert_commit(target_commit.hexsha)
            else:
                response = f"❌ Commit `{commit_id}` not found in last 20."
        else:
            response = "❗ Please specify a valid commit hash to revert."
    else:
        response = "🤖 I can help with:\n- `show commits`\n- `revert abc123`\n- `show log`"

    st.session_state.chat_history.append(("assistant", response))
    with st.chat_message("assistant"):
        st.markdown(response)
