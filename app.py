import streamlit as st
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# TIMEZONE
# ============================================
TT_TZ = ZoneInfo("America/Port_of_Spain")
def get_tt_date():
    return datetime.now(TT_TZ).date()

# ============================================
# CACHED GEMINI & SHEETS
# ============================================
@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=st.secrets["google_api_key"])
    return genai.GenerativeModel(
        "models/gemini-flash-latest",
        generation_config={"temperature": 0.7, "max_output_tokens": 500, "top_p": 0.8}
    )

@st.cache_resource
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["google_sheets"],
            scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds).open("SEA_Math_Tutor_Data")
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return None

# ============================================
# FULL SYSTEM PROMPT (Gemini CANNOT mention badges)
# ============================================
SYSTEM_PROMPT = """You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.
============================================================
CRITICAL IDENTITY RULES
============================================================
ROLE:
- You are a friendly, encouraging AI math tutor for 11-year-olds.
- You create SEA curriculum–aligned questions.
- You explain answers simply and kindly.
- You NEVER speak harshly or discourage the student.
YOU MUST NOT:
- You MUST NOT award badges.
- You MUST NOT calculate streaks.
- You MUST NOT say “you got X correct so far.”
- You MUST NOT invent badge names or achievements.
- You MUST NOT reference progress (“You are doing well today because…”).
- You MUST NOT show or mention “user:” or “assistant:” in any reply.
- You MUST NOT show the answer when asking a question.
- You MUST NOT answer your own question.
- You MUST wait for the student’s answer before giving feedback.
Only the APP calculates correctness, streaks, progress, and badges — NOT YOU.
[All your original strict rules continue here — unchanged]
You are helping them become math champions! 🏆
"""

# ============================================
# PAGE CONFIG + FIXED CSS (Progress chart now visible!)
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
    
    /* FIX: Make progress expander text and content visible */
    .stExpander > div > label {color: #111827 !important; font-weight: 600;}
    .stExpander .stMarkdown {color: #111827 !important;}
    </style>
    """, unsafe_allow_html=True)
load_css()

# ============================================
# SESSION STATE + STREAK
# ============================================
defaults = {
    "screen": "dashboard", "student_name": None, "first_name": None, "student_id": None,
    "current_topic": None, "questions_answered": 0, "correct_answers": 0,
    "current_streak": 0, "best_streak": 0,
    "session_start": None, "conversation_history": [], "question_start_time": datetime.now(TT_TZ),
    "daily_usage": {"date": get_tt_date().isoformat(), "count": 0}, "pending_logs": []
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ============================================
# GLOBAL BADGE SYSTEM
# ============================================
def award_global_badge(streak):
    name = st.session_state.first_name.split()[0] if st.session_state.first_name else "Champion"
    if streak == 5:
        st.balloons()
        st.success(f"🎖️ **BRONZE STAR** – {name}, 5 in a row! Keep shining! ✨")
    elif streak == 10:
        st.snow()
        st.success(f"🏆 **SILVER TROPHY** – {name} hits 10 perfect! Unstoppable! 🚀")
    elif streak == 15:
        st.balloons()
        st.success(f"🥇 **GOLD MEDAL** – {name} scores 15 in a row! Champion! 🏆")
    elif streak == 20:
        st.fireworks()
        st.success(f"👑 **PLATINUM CROWN** – {name} reaches 20! You're royalty! 👑")
    elif streak == 25:
        st.fireworks()
        st.toast("💎 DIAMOND LEGEND UNLOCKED!", icon="💎")
        st.balloons()
        st.success(f"💎 **DIAMOND LEGEND** – {name} got 25 in a row! SEA HISTORY! 🌟")

# ============================================
# SHEETS LOGGING
# ============================================
def flush_logs():
    if st.session_state.pending_logs:
        try:
            get_sheets_client().worksheet("Activity_Log").append_rows(st.session_state.pending_logs)
            st.session_state.pending_logs.clear()
        except: pass

def log_student_activity(sid, name, qtype, strand, correct, secs):
    ts = datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.pending_logs.append([ts, sid, name, qtype, strand, "Yes" if correct else "No", secs])
    st.session_state.daily_usage["count"] += 1
    if len(st.session_state.pending_logs) >= 5: flush_logs()

# (Keep your get_or_create_student_id, update_student_summary, check_global_limit, check_daily_limit exactly as before)

# ============================================
# CHAT SESSION
# ============================================
def get_or_create_chat():
    if "gemini_chat" not in st.session_state:
        chat = get_gemini_model().start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood!"]}
        ])
        st.session_state.gemini_chat = chat
    return st.session_state.gemini_chat

# ============================================
# PRACTICE SCREEN (WITH BADGES + STREAK)
# ============================================
def show_practice_screen():
    check_global_limit()
    check_daily_limit()

    col1, col2 = st.columns([5,1])
    with col1:
        icons = {"Number":"🔢","Measurement":"📏","Geometry":"📐","Statistics":"📊","Mixed":"🎲","Full Test":"📝"}
        st.title(f"{icons.get(st.session_state.current_topic,'📚')} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("🚪 Exit"):
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
            st.session_state.screen = "dashboard"
            st.rerun()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Questions", st.session_state.questions_answered)
    with c2: st.metric("Correct", st.session_state.correct_answers)
    with c3:
        acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered,1) * 100)
        st.metric("Accuracy", f"{acc}%")
    with c4: st.metric("🔥 Streak", st.session_state.current_streak if st.session_state.current_streak else "—")

    st.write("---")

    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.write(msg["content"])

    if not st.session_state.conversation_history:
        st.info(f"👋 Hi {st.session_state.first_name}! Type **Start** or **Next** to begin!")

    if prompt := st.chat_input("Type your answer or say 'Next'…"):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.write(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                resp = get_or_create_chat().send_message(
                    f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}"
                )
                text = resp.text
                st.write(text)
                st.session_state.conversation_history.append({"role": "assistant", "content": text})

                # GLOBAL STREAK + BADGE LOGIC
                first = text.splitlines()[0].strip().lower()
                correct = any(x in first for x in ["correct","yes!","excellent","great job","well done","perfect","right","you got it"])
                wrong   = any(x in first for x in ["not quite","not correct","try again","wrong","almost"])

                if correct or wrong:
                    st.session_state.questions_answered += 1
                    if correct:
                        st.session_state.correct_answers += 1
                        st.session_state.current_streak += 1
                        if st.session_state.current_streak > st.session_state.best_streak:
                            st.session_state.best_streak = st.session_state.current_streak
                        if st.session_state.current_streak in [5,10,15,20,25]:
                            award_global_badge(st.session_state.current_streak)
                    else:
                        if st.session_state.current_streak >= 5:
                            st.info(f"🔥 Streak ended at {st.session_state.current_streak} — amazing effort! 💪")
                        st.session_state.current_streak = 0

                    elapsed = (datetime.now(TT_TZ) - st.session_state.question_start_time).total_seconds()
                    log_student_activity(st.session_state.student_id, st.session_state.student_name,
                                         "Question", st.session_state.current_topic, correct, int(elapsed))
                    st.session_state.question_start_time = datetime.now(TT_TZ)

# ============================================
# DASHBOARD (with fixed progress modal)
# ============================================
def show_progress_modal():
    with st.expander("📊 Your Progress Today", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Questions", st.session_state.questions_answered)
        with col2:
            acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered,1) * 100)
            st.metric("Accuracy", f"{acc}%")
        with col3:
            DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
            remaining = DAILY_LIMIT - st.session_state.daily_usage["count"]
            st.metric("Left Today", max(remaining, 0))
        st.progress(min(st.session_state.daily_usage["count"] / DAILY_LIMIT, 1.0))
        if st.session_state.current_streak:
            st.success(f"🔥 Current Streak: **{st.session_state.current_streak}**")
        if st.session_state.best_streak:
            st.info(f"🏆 Your Best Streak Ever: **{st.session_state.best_streak}**")

# (Keep your full show_dashboard(), start_practice(), and other functions exactly as before)

# ============================================
# MAIN
# ============================================
if st.session_state.screen == "practice":
    show_practice_screen()
else:
    show_dashboard()
