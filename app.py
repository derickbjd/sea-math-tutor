import streamlit as st
import google.generativeai as genai
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="SEA Math Super-Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CUSTOM CSS
# ============================================

def load_css():
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    .stButton button {
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    div[data-testid="column"] > div > div > button {
        height: 120px;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

defaults = {
    'screen': 'dashboard',
    'student_name': None,
    'student_id': None,
    'first_name': None,
    'current_topic': None,
    'questions_answered': 0,
    'correct_answers': 0,
    'session_start': None,
    'conversation_history': [],
    'daily_usage': {'date': date.today().isoformat(), 'count': 0},
    'badge_progress': {
        'number': 0,
        'measurement': 0,
        'geometry': 0,
        'statistics': 0
    }
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================

def connect_to_sheets():
    try:
        creds_info = st.secrets["google_sheets"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("SEA_Math_Tutor_Data")
        return sheet
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None

def log_student_activity(student_id, student_name, question_type, strand, correct, time_seconds):
    try:
        sheet = connect_to_sheets()
        if sheet:
            activity = sheet.worksheet("Activity_Log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            activity.append_row([
                timestamp, student_id, student_name,
                question_type, strand,
                "Yes" if correct else "No",
                time_seconds
            ])
            st.session_state.daily_usage['count'] += 1
    except Exception:
        pass

def update_student_summary(student_id, student_name):
    try:
        sheet = connect_to_sheets()
        if sheet:
            students = sheet.worksheet("Students")
            try:
                cell = students.find(student_id)
                row = cell.row
                accuracy = (
                    round((st.session_state.correct_answers /
                           st.session_state.questions_answered * 100), 1)
                    if st.session_state.questions_answered > 0 else 0
                )
                minutes = round((datetime.now() -
                                 st.session_state.session_start).seconds / 60)

                students.update_cell(row, 4, st.session_state.questions_answered)
                students.update_cell(row, 5, st.session_state.correct_answers)
                students.update_cell(row, 6, f"{accuracy}%")
                prev_minutes = int(students.cell(row, 7).value or 0)
                students.update_cell(row, 7, prev_minutes + minutes)
                students.update_cell(row, 8, datetime.now().strftime("%Y-%m-%d %H:%M"))
            except Exception:
                students.append_row([
                    student_id, student_name,
                    datetime.now().strftime("%Y-%m-%d"),
                    st.session_state.questions_answered,
                    st.session_state.correct_answers,
                    f"{accuracy}%",
                    minutes,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])
    except Exception:
        pass

# ============================================
# PROTECTION LIMITS
# ============================================

def check_global_limit():
    GLOBAL = int(st.secrets.get("global_daily_limit", 1000))
    try:
        sheet = connect_to_sheets()
        if sheet:
            activity = sheet.worksheet("Activity_Log")
            today = date.today().isoformat()
            records = activity.get_all_records()
            count_today = sum(
                1 for r in records
                if str(r.get("Timestamp", "")).startswith(today)
            )
            if count_today >= GLOBAL:
                st.error("🚨 Daily Capacity Reached")
                st.stop()
    except Exception:
        pass

def check_daily_limit():
    DAILY = int(st.secrets.get("daily_limit_per_student", 50))
    today = date.today().isoformat()

    if st.session_state.daily_usage['date'] != today:
        st.session_state.daily_usage = {'date': today, 'count': 0}

    if st.session_state.daily_usage['count'] >= DAILY:
        st.warning("🎯 Daily Practice Goal Reached!")
        st.stop()

# ============================================
# AI CONFIGURATION
# ============================================

def configure_gemini():
    try:
        genai.configure(api_key=st.secrets["google_api_key"])
        return genai.GenerativeModel("models/gemini-1.5-flash")
    except Exception as e:
        st.error(f"Could not configure AI: {e}")
        return None

SYSTEM_PROMPT = """You are the SEA Math Super-Tutor...
(keeping your full prompt unchanged)
"""

# ============================================
# DASHBOARD UI
# ============================================

def show_dashboard():
    st.markdown("""
    <h1 style='text-align:center;'>🎓 SEA Math Super-Tutor</h1>
    """, unsafe_allow_html=True)

    if not st.session_state.student_name:
        first = st.text_input("First Name")
        last = st.text_input("Last Name")
        code = st.text_input("Class Code", type="password")

        if st.button("Enter"):
            valid_codes = st.secrets.get("class_codes", "MATH2025").split(",")
            if code.upper().strip() in [c.strip().upper() for c in valid_codes]:
                st.session_state.student_name = f"{first} {last}"
                st.session_state.first_name = first
                st.session_state.student_id = f"STU{abs(hash(first+last+str(datetime.now())))}"[:10]
                st.session_state.session_start = datetime.now()
                st.rerun()
            else:
                st.error("Invalid class code.")
        return

    check_global_limit()
    check_daily_limit()

    st.write(f"### Welcome, {st.session_state.first_name}! 🎉")

    if st.button("Start Number"):
        start_practice("Number")
    if st.button("Start Geometry"):
        start_practice("Geometry")
    if st.button("Start Measurement"):
        start_practice("Measurement")
    if st.button("Start Statistics"):
        start_practice("Statistics")

def start_practice(topic):
    st.session_state.current_topic = topic
    st.session_state.screen = "practice"
    st.session_state.conversation_history = []
    st.rerun()

# ============================================
# PRACTICE SCREEN
# ============================================

def show_practice_screen():
    check_global_limit()
    check_daily_limit()

    st.title(f"{st.session_state.current_topic} Practice")

    model = configure_gemini()

    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Start or answer here...")
    if user_input:
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        full_prompt = SYSTEM_PROMPT + "\n\n"
        for m in st.session_state.conversation_history[-10:]:
            full_prompt += f"{m['role']}: {m['content']}\n"

        response = model.generate_content(full_prompt)
        text = response.text

        st.session_state.conversation_history.append({"role": "assistant", "content": text})

        with st.chat_message("assistant"):
            st.write(text)

# ============================================
# MAIN ROUTER
# ============================================

def main():
    if st.session_state.screen == "practice":
        show_practice_screen()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
