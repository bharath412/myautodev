import os
from pathlib import Path
import streamlit as st

# Project Paths
PROJECT_ROOT_PATH = "E:/ERP/dev/CursorAI2/myautodev"
PROJECT_ROOT = Path(PROJECT_ROOT_PATH)
JAVA_SRC_DIRS = ['src/main/java', 'src/test/java']
STATIC_SRC_DIR = 'src/main/resources/static'
ROBOT_TESTS_PATH_STR = "E:/ERP/dev/CursorAI2/myautodev/src/test/robotframework"
relative_robot_path_str = "src/test/robotframework"

# Git Configuration
GIT_REPO_URL = "https://github.com/bharath412/myautodev.git"
GIT_COMMIT_MESSAGE = "feat: AI-assisted code changes and test updates"

# Gemini Configuration
MODEL_NAME = "gemini-1.5-pro-latest"
generation_config = {
    "temperature": 0.7,
    "top_p": 1.0,
    "top_k": 1,
    "max_output_tokens": 8192,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize API Key
try:
    API_KEY = st.secrets.get("GEMINI_API_KEY")
    if not API_KEY:
        API_KEY = os.environ.get("GEMINI_API_KEY")
except AttributeError:
    API_KEY = os.environ.get("GEMINI_API_KEY")