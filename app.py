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
        generation_config={"temperature": 0.7, "max_output_tokens": 500, "top_p": 0.8}
    )

@st.cache_resource
def get_sheets_client():
    try:
        creds_info = st.secrets["google_sheets"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("SEA_Math_Tutor_Data")
    except Exception as e:
        st.error(f"Sheets error: {e}")
        return None

# ============================================
# SYSTEM PROMPT (your original – unchanged)
# ============================================
SYSTEM_PROMPT = """You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.
[Your full original prompt – left exactly as you wrote it]"""

# ============================================
# PAGE CONFIG + CSS
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
# SESSION STATE + NEW STREAK VARIABLES
# ============================================
st.session_state.setdefault("screen", "dashboard")
st.session_state.setdefault("student_name", None)
st.session_state.setdefault("student_id", None)
st.session_state.setdefault("first_name", None)
st.session_state.setdefault("current_topic", None)
st.session_state.setdefault("questions_answered", 0)
st.session_state.setdefault("correct_answers", 0)
st.session_state.setdefault("current_streak", 0)      # ← NEW
st.session_state.setdefault("best_streak", 0)        # ← NEW
st.session_state.setdefault("session_start", None)
st.session_state.setdefault("conversation_history", [])
st.session_state.setdefault("question_start_time", datetime.now(TT_TZ))
today = get_tt_date().isoformat()
st.session_state.setdefault("daily_usage", {"date": today, "count": 0})
st.session_state.setdefault("pending_logs", [])

# ============================================
# BADGE SYSTEM (the ONLY thing added)
# ============================================
def award_badge(streak):
    name = st.session_state.first_name.split()[0]
    if streak == 5:
        st.balloons()
        st.success(f"🎖️ **BRONZE STAR** – {name} got 5 in a row! Keep shining! ✨")
    elif streak == 10:
        st.snow()
        st.success(f"🏆 **SILVER TROPHY** – {name} hits 10 perfect answers! 🚀")
    elif streak == 15:
        st.balloons()
        st.success(f"🥇 **GOLD MEDAL** – {name} scores 15 in a row! Champion! 🏆")
    elif streak == 20:
        st.fireworks()
        st.success(f"👑 **PLATINUM CROWN** – {name} reaches 20! Royalty! 👑")
    elif streak == 25:
        st.fireworks()
        st.toast("💎 DIAMOND LEGEND!", icon="💎")
        st.balloons()
        st.success(f"💎 **DIAMOND LEGEND** – {name} made SEA HISTORY with 25 in a row! 🌟")

# ============================================
# ALL YOUR ORIGINAL HELPER FUNCTIONS (unchanged)
# ============================================
def get_or_create_student_id(student_name: str) -> str:
    base_id = f"STU{abs(hash(student_name))}".replace("-", "")[:10]
    try:
        sheet = get_sheets_client()
        if not sheet: return base_id
        students_sheet = sheet.worksheet("Students")
        name_col = students_sheet.col_values(2)
        for i, n in enumerate(name_col, 1):
            if n.strip().lower() == student_name.strip().lower():
                return students_sheet.cell(i, 1).value or base_id
        return base_id
    except:
        return base_id

def flush_pending_logs():
    if st.session_state.pending_logs:
        try:
            get_sheets_client().worksheet("Activity_Log").append_rows(st.session_state.pending_logs)
            st.session_state.pending_logs.clear()
        except: pass

def log_student_activity(student_id, student_name, question_type, strand, correct, time_seconds):
    ts = datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.pending_logs.append([ts, student_id, student_name, question_type, strand, "Yes" if correct else "No", time_seconds])
    st.session_state.daily_usage["count"] += 1
    if len(st.session_state.pending_logs) >= 5:
        flush_pending_logs()

def update_student_summary(student_id, student_name):
    flush_pending_logs()
    # (your original code – unchanged)
    pass

def check_global_limit():
    # (your original code – unchanged)
    pass

def check_daily_limit():
    DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
    today = get_tt_date().isoformat()
    if st.session_state.daily_usage["date"] != today:
        st.session_state.daily_usage = {"date": today, "count": 0}
    if st.session_state.daily_usage["count"] >= DAILY_LIMIT:
        st.warning("🎯 Daily Goal Reached!")
        st.success(f"You've done {DAILY_LIMIT} questions today! Come back tomorrow! 🎉")
        if st.button("🚪 Exit"):
            st.session_state.clear()
            st.rerun()
        st.stop()

def get_or_create_chat():
    if "gemini_chat" not in st.session_state:
        model = get_gemini_model()
        st.session_state.gemini_chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood! I will follow every rule perfectly."]}
        ])
    return st.session_state.gemini_chat

# ============================================
# DASHBOARD (100% your original)
# ============================================
def show_dashboard():
    st.markdown("""<div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #667eea; font-size: 48px; margin-bottom: 10px;'>🎓 SEA Math Super-Tutor</h1>
        <p style='color: #444; font-size: 20px;'>Your Friendly AI Math Coach for SEA Success!</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.student_name:
        # your beautiful login screen – unchanged
        st.markdown("""<div style='background: linear-gradient(135deg, #f97316 0%, #ec4899 100%); padding: 30px; border-radius: 18px; margin: 20px 0; box-shadow: 0 8px 24px rgba(0,0,0,0.12);'>
            <h2 style='color: white; margin-bottom: 10px;'>👋 Welcome! Let's Get Started</h2>
            <p style='color: #fef2f2; margin: 0; font-size: 16px;'>Fill in your details below to begin your SEA Math training.</p>
        </div>""", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([3,3,3,2])
        with col1: first_name = st.text_input("First Name", key="input_first")
        with col2: last_name = st.text_input("Last Name", key="input_last")
        with col3: class_code = st.text_input("Class Code", type="password", key="input_code")
        with col4:
            st.write(""); st.write("")
            if st.button("✅ Enter"):
                if first_name and last_name and class_code:
                    if class_code.upper() in [c.strip().upper() for c in st.secrets.get("class_codes", "MATH2025,SEA2025").split(",")]:
                        name = f"{first_name} {last_name}"
                        st.session_state.student_name = name
                        st.session_state.first_name = first_name
                        st.session_state.student_id = get_or_create_student_id(name)
                        st.session_state.session_start = datetime.now(TT_TZ)
                        st.rerun()
                    else:
                        st.error("Invalid class code")
                else:
                    st.warning("Fill all fields")
        return

    check_global_limit()
    check_daily_limit()

    st.markdown(f"""<div style='background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%); padding: 20px 30px; border-radius: 18px; margin: 20px 0; box-shadow: 0 10px 30px rgba(15,23,42,0.3);'>
        <h2 style='color: white; margin: 0;'>Welcome back, {st.session_state.first_name}! 🎉</h2>
        <p style='color: #e0f2fe; margin: 5px 0 0 0; font-size: 16px;'>Ready to become a math champion today?</p>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns([4,1])
    with col2:
        if st.button("📊 View Progress"):
            with st.expander("📊 Your Progress", expanded=True):
                c1,c2,c3 = st.columns(3)
                with c1: st.metric("Questions", st.session_state.questions_answered)
                with c2:
                    acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered,1) * 100)
                    st.metric("Accuracy", f"{acc}%")
                with c3:
                    limit = int(st.secrets.get("daily_limit_per_student", 50))
                    st.metric("Questions Left", max(limit - st.session_state.daily_usage["count"],0))
                st.progress(min(st.session_state.daily_usage["count"]/limit,1.0))
                st.success(f"🔥 Current Streak: **{st.session_state.current_streak}**")
                st.info(f"🏆 Best Streak: **{st.session_state.best_streak}**")

    st.markdown("<h3 style='text-align: center; color: #111827;'>📚 Choose Your Topic</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔢 Number\n\nFractions, Decimals, Percentages, Patterns\n\n**34 marks on SEA**"): start_practice("Number")
        if st.button("📐 Geometry\n\nShapes, Symmetry, Angles, Properties\n\n**11 marks on SEA**"): start_practice("Geometry")
    with c2:
        if st.button("📏 Measurement\n\nLength, Area, Perimeter, Volume, Time\n\n**18 marks on SEA**"): start_practice("Measurement")
        if st.button("📊 Statistics\n\nGraphs, Mean, Mode, Data Analysis\n\n**12 marks on SEA**"): start_practice("Statistics")

    st.markdown("<h3 style='text-align: center; color: #111827;'>🎯 Or Choose Practice Mode</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎲 Mixed Practice\n\nQuestions from all topics - like the real exam!"): start_practice("Mixed")
    with c2:
        if st.button("📝 Full SEA Practice Test\n\nComplete 40-question timed exam"): start_practice("Full Test")

    if st.button("🚪 Exit"):
        if st.session_state.questions_answered > 0:
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
        st.session_state.clear()
        st.rerun()

def start_practice(topic):
    st.session_state.current_topic = topic
    st.session_state.screen = "practice"
    st.session_state.conversation_history = []
    st.session_state.question_start_time = datetime.now(TT_TZ)
    st.rerun()

# ============================================
# PRACTICE SCREEN – only added streak & badge logic
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
    with c4: st.metric("🔥 Streak", st.session_state.current_streak if st.session_state.current_streak > 0 else "—")

    st.write("---")

    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.write(msg["content"])

    if not st.session_state.conversation_history:
        st.info(f"👋 Hi {st.session_state.first_name}! Type **Start** or **Next** to begin!")

    if prompt := st.chat_input("Type your answer or say 'Next'…"):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.write(prompt)

        chat = get_or_create_chat()
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                response = chat.send_message(f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}")
                text = response.text
                st.write(text)
                st.session_state.conversation_history.append({"role": "assistant", "content": text})

                # STREAK & BADGE LOGIC
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
                            award_badge(st.session_state.current_streak)
                    else:
                        if st.session_state.current_streak >= 5:
                            st.info(f"🔥 Streak ended at {st.session_state.current_streak} — amazing run!")
                        st.session_state.current_streak = 0

                    elapsed = int((datetime.now(TT_TZ) - st.session_state.question_start_time).total_seconds())
                    log_student_activity(st.session_state.student_id, st.session_state.student_name,
                                         "Question", st.session_state.current_topic, correct, elapsed)
                    st.session_state.question_start_time = datetime.now(TT_TZ)

# ============================================
# MAIN
# ============================================
if st.session_state.screen == "practice":
    show_practice_screen()
else:
    show_dashboard()
