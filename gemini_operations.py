import google.generativeai as genai
import streamlit as st
import re
from pathlib import Path
from config import MODEL_NAME, generation_config, safety_settings, PROJECT_ROOT

def init_gemini():
    """Initialize Gemini model and chat"""
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
        st.stop()

def parse_gemini_response(response_text):
    """Parse Gemini response for code blocks and file paths"""
    parsed_data = []
    pattern = re.compile(
        r"--- START FILE: (.*?) ---\s*```(java|html|css|javascript|robotframework|xml|properties|md|)?\s*(.*?)\s*```\s*--- END FILE: \1 ---",
        re.DOTALL | re.IGNORECASE
    )
    
    matches = pattern.finditer(response_text)
    for match in matches:
        relative_path_str = match.group(1).strip().replace('\\', '/')
        language = match.group(2).strip().lower() if match.group(2) else None
        code_content = match.group(3).strip()

        if ".." in relative_path_str:
            st.warning(f"Skipping potentially unsafe path: '{relative_path_str}'")
            continue

        # Process the matched content and create the parsed data
        parsed_entry = process_matched_content(relative_path_str, language, code_content)
        if parsed_entry:
            parsed_data.append(parsed_entry)

    return parsed_data

def process_matched_content(relative_path_str, language, code_content):
    """Process matched content from Gemini response"""
    relative_path_obj = Path(relative_path_str)
    absolute_path = determine_absolute_path(relative_path_obj)
    
    if absolute_path:
        if not language:
            language = get_file_language(absolute_path)
        
        return {
            "relative_path": relative_path_str,
            "absolute_path": str(absolute_path),
            "language": language or "plaintext",
            "code": code_content
        }
    return None