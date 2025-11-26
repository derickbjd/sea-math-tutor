import streamlit as st
import google.generativeai as genai
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import time

# ============================================
# TIMEZONE
# ============================================
TT_TZ = ZoneInfo("America/Port_of_Spain")
def get_tt_date():
    return datetime.now(TT_TZ).date()

# ============================================
# CACHED RESOURCES
# ============================================
@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=st.secrets["google_api_key"])
    return genai.GenerativeModel(
        "models/gemini-flash-latest",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 500,
            "top_p": 0.8,
        }
    )

@st.cache_resource
def get_sheets_client():
    try:
        creds_info = st.secrets["google_sheets"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("SEA_Math_Tutor_Data")
        return sheet
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None

# ============================================
# SYSTEM PROMPT (unchanged)
# ============================================
SYSTEM_PROMPT = """You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.
[Your full original prompt continues here — unchanged]"""

# ============================================
# PAGE CONFIG + CSS (unchanged)
# ============================================
st.set_page_config(page_title="SEA Math Super-Tutor", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

def load_css():
    st.markdown("""
    <style>
    .stApp {background-color: #f5f7fb;}
    table, th, td {color: #111827 !important; border-color: #9ca3af !important;}
    thead th {background-color: #e5e7eb !important; color: #111827 !important;}
    tbody td {background-color: #ffffff !important;}
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    .stChatMessage .stMarkdown p, .stChatMessage .stMarkdown li {color: #111827 !important;}
    [data-testid="stChatMessage"] > div:first-child {display: none !important;}
    .stChatMessage[data-testid="stChatMessageUser"] {background-color: #e0f2fe !important; border-radius: 14px; padding: 0.75rem 1rem;}
    .stChatMessage[data-testid="stChatMessageAssistant"] {background-color: #ffffff !important; border-radius: 14px; padding: 0.75rem 1rem;}
    .stButton > button {
        border-radius: 14px; font-weight: 700; border: none; padding: 0.85rem 1.1rem;
        font-size: 1.05rem; color: #fff !important;
        background: linear-gradient(135deg, #4f46e5, #6366f1);
        box-shadow: 0 4px 10px rgba(79,70,229,0.25);
    }
    div[data-testid="column"] > div > div > button {min-height: 120px; white-space: pre-wrap;}
    </style>
    """, unsafe_allow_html=True)
load_css()

# ============================================
# SESSION STATE (added streak + best streak)
# ============================================
st.session_state.setdefault("screen", "dashboard")
st.session_state.setdefault("student_name", None)
st.session_state.setdefault("student_id", None)
st.session_state.setdefault("first_name", None)
st.session_state.setdefault("current_topic", None)
st.session_state.setdefault("questions_answered", 0)
st.session_state.setdefault("correct_answers", 0)
st.session_state.setdefault("current_streak", 0)        # ← NEW
st.session_state.setdefault("best_streak", 0)          # ← NEW
st.session_state.setdefault("session_start", None)
st.session_state.setdefault("conversation_history", [])
today = get_tt_date().isoformat()
st.session_state.setdefault("daily_usage", {"date": today, "count": 0})
st.session_state.setdefault("pending_logs", [])

# ============================================
# NEW: GLOBAL BADGE SYSTEM (only addition!)
# ============================================
def award_badge(streak):
    name = st.session_state.first_name.split()[0]
    if streak == 5:
        st.balloons()
        st.success(f"BRONZE STAR UNLOCKED, {name}! 5 in a row! Keep shining! ✨")
    elif streak == 10:
        st.snow()
        st.success(f"SILVER TROPHY, {name}! Perfect 10! Unstoppable! 🚀")
    elif streak == 15:
        st.balloons()
        st.success(f"GOLD MEDAL, {name}! 15 correct in a row! Champion! 🏆")
    elif streak == 20:
        st.fireworks()
        st.success(f"PLATINUM CROWN, {name}! 20 in a row — You're royalty! 👑")
    elif streak == 25:
        st.fireworks()
        st.toast("DIAMOND LEGEND ACHIEVED!", icon="💎")
        st.balloons()
        st.success(f"DIAMOND LEGEND, {name}! 25 in a row — SEA HISTORY MADE! 🌟")

# ============================================
# [All your original functions unchanged: get_or_create_student_id, flush_pending_logs, etc.]
# ============================================
# ... (keeping everything exactly as you had it)

# ============================================
# PRACTICE SCREEN — ONLY ADDED STREAK + BADGE LOGIC
# ============================================
def show_practice_screen():
    check_global_limit()
    check_daily_limit()

    col1, col2 = st.columns([5, 1])
    with col1:
        topic_icons = {"Number": "Number","Measurement": "Measurement","Geometry": "Geometry","Statistics": "Statistics","Mixed": "Mixed","Full Test": "Full Test"}
        icon = topic_icons.get(st.session_state.current_topic, "Book")
        st.title(f"{icon} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("Exit"):
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
            st.session_state.screen = "dashboard"
            st.session_state.current_topic = None
            st.rerun()

    # Stats bar — added streak
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Questions", st.session_state.questions_answered)
    with col2: st.metric("Correct", st.session_state.correct_answers)
    with col3:
        acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered,1) * 100)
        st.metric("Accuracy", f"{acc}%")
    with col4: st.metric("Streak", st.session_state.current_streak if st.session_state.current_streak > 0 else "—")  # ← NEW

    st.write("---")

    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"], avatar="Robot" if message["role"] == "assistant" else "Person"):
            st.write(message["content"])

    if len(st.session_state.conversation_history) == 0:
        st.info(f"Hi {st.session_state.first_name}! Type **Start** or **Next** to begin!")

    if prompt := st.chat_input("Type your answer or 'Next' for a question..."):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="Person"): st.write(prompt)

        chat = get_or_create_chat()
        with st.chat_message("assistant", avatar="Robot"):
            with st.spinner("Thinking..."):
                context = f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}"
                response = chat.send_message(context)
                text = response.text
                st.write(text)
                st.session_state.conversation_history.append({"role": "assistant", "content": text})

                # CORRECTNESS + STREAK + BADGE LOGIC (only new part)
                first_line = text.splitlines()[0].strip().lower()
                correct = any(x in first_line for x in ["correct","yes!","excellent","great job","well done","perfect","right","you got it"])
                wrong   = any(x in first_line for x in ["not quite","not correct","try again","wrong","almost"])

                if correct or wrong:
                    st.session_state.questions_answered += 1
                    if correct:
                        st.session_state.correct_answers += 1
                        st.session_state.current_streak += 1
                        if st.session_state.current_streak > st.session_state.best_streak:
                            st.session_state.best_streak = st.session_state.current_streak
                        if st.session_state.current_streak in [5,10,15,20,25]:
                            award_badge(st.session_state.current_streak)
                    else:
                        if st.session_state.current_streak >= 5:
                            st.info(f"Streak ended at {st.session_state.current_streak} — incredible run! Keep going!")
                        st.session_state.current_streak = 0

                    # Log time
                    question_start = st.session_state.get("question_start_time", datetime.now(TT_TZ))
                    elapsed = int((datetime.now(TT_TZ) - question_start).total_seconds())
                    log_student_activity(
                        st.session_state.student_id,
                        st.session_state.student_name,
                        "Question",
                        st.session_state.current_topic,
                        correct,
                        elapsed,
                    )
                    st.session_state.question_start_time = datetime.now(TT_TZ)

# ============================================
# DASHBOARD & MAIN (unchanged — just added streak to progress modal)
# ============================================
def show_progress_modal():
    with st.expander("Your Progress", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Questions Today", st.session_state.questions_answered)
        with col2:
            acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered,1) * 100)
            st.metric("Accuracy", f"{acc}%")
        with col3:
            DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
            remaining = DAILY_LIMIT - st.session_state.daily_usage["count"]
            st.metric("Questions Left", remaining)
        st.progress(min(st.session_state.daily_usage["count"] / DAILY_LIMIT, 1.0))
        # ← Added streak display
        st.success(f"Current Streak: **{st.session_state.current_streak}**")
        st.info(f"Best Streak Ever: **{st.session_state.best_streak}**")

# [All your original show_dashboard(), start_practice(), main() — unchanged]

# ============================================
# MAIN
# ============================================
def main():
    if st.session_state.screen == "practice":
        show_practice_screen()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
