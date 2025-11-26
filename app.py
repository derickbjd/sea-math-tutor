import streamlit as st
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# TIMEZONE & RESOURCES
# ============================================
TT_TZ = ZoneInfo("America/Port_of_Spain")
def get_tt_date():
    return datetime.now(TT_TZ).date()

@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=st.secrets["google_api_key"])
    return genai.GenerativeModel("models/gemini-flash-latest",
        generation_config={"temperature": 0.7, "max_output_tokens": 500, "top_p": 0.8})

@st.cache_resource
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(st.secrets["google_sheets"],
            scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open("SEA_Math_Tutor_Data")
    except:
        return None

# ============================================
# SYSTEM PROMPT (Gemini never mentions badges)
# ============================================
SYSTEM_PROMPT = """You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.
You are kind, encouraging, and never mention badges, streaks, or progress counts.
When asking a question, end with: "This is a [Topic] question."
When answering, start with "Correct!" or "Not quite".
Only the app awards badges — NEVER you.
You are helping them become math champions!"""

# ============================================
# BEAUTIFUL CSS + PAGE SETUP
# ============================================
st.set_page_config(page_title="SEA Math Super-Tutor", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp {background-color: #f5f7fb;}
#MainMenu, footer, header, .stDeployButton {visibility: hidden;}
.stChatMessage .stMarkdown p {color: #111827 !important;}
[data-testid="stChatMessage"] > div:first-child {display: none !important;}
.stChatMessage[data-testid="stChatMessageUser"] {background-color: #e0f2fe !important; border-radius: 14px; padding: 1rem;}
.stChatMessage[data-testid="stChatMessageAssistant"] {background-color: #ffffff !important; border-radius: 14px; padding: 1rem;}
.stButton > button {
    border-radius: 16px; font-weight: 700; border: none; padding: 1.2rem;
    font-size: 1.3rem; color: white !important; height: 140px; width: 100%;
    background: linear-gradient(135deg, #4f46e5, #6366f1);
    box-shadow: 0 6px 15px rgba(79,70,229,0.3);
}
.stExpander > div > label {color: #111827 !important; font-size: 1.2rem; font-weight: 700;}
</style>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE + STREAK
# ============================================
st.session_state.setdefault("screen", "dashboard")
st.session_state.setdefault("student_name", None)
st.session_state.setdefault("first_name", None)
st.session_state.setdefault("student_id", None)
st.session_state.setdefault("current_topic", None)
st.session_state.setdefault("questions_answered", 0)
st.session_state.setdefault("correct_answers", 0)
st.session_state.setdefault("current_streak", 0)
st.session_state.setdefault("best_streak", 0)
st.session_state.setdefault("conversation_history", [])
st.session_state.setdefault("question_start_time", datetime.now(TT_TZ))

# ============================================
# BADGE CELEBRATION (SAFE
# ============================================
def award_badge(streak):
    name = st.session_state.first_name.split()[0]
    if streak == 5:
        st.balloons()
        st.success(f"🎖️ BRONZE STAR! {name} got 5 in a row! 🔥")
    elif streak == 10:
        st.snow()
        st.success(f"🏆 SILVER TROPHY! {name} — Perfect 10! 🚀")
    elif streak == 15:
        st.balloons()
        st.success(f"🥇 GOLD MEDAL! {name} — 15 correct! Legend! 🌟")
    elif streak == 20:
        st.fireworks()
        st.success(f"👑 PLATINUM CROWN! {name} — 20 in a row! Royalty! 👑")
    elif streak == 25:
        st.fireworks()
        st.balloons()
        st.toast("💎 DIAMOND LEGEND!", icon="💎")
        st.success(f"💎 DIAMOND LEGEND! {name} made SEA HISTORY! 🏆")

# ============================================
# PRACTICE SCREEN
# ============================================
def show_practice_screen():
    # Header
    col1, col2 = st.columns([6,1])
    with col1:
        icons = {"Number":"🔢","Measurement":"📏","Geometry":"📐","Statistics":"📊","Mixed":"🎲","Full Test":"📝"}
        st.title(f"{icons[st.session_state.current_topic]} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("🚪 Exit"):
            st.session_state.screen = "dashboard"
            st.rerun()

    # Stats
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Questions", st.session_state.questions_answered)
    with c2: st.metric("Correct", st.session_state.correct_answers)
    with c3: st.metric("Accuracy", f"{round(st.session_state.correct_answers/max(st.session_state.questions_answered,1)*100)}%")
    with c4: st.metric("🔥 Streak", st.session_state.current_streak if st.session_state.current_streak else "—")

    st.write("---")

    # Chat
    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.markdown(msg["content"])

    if not st.session_state.conversation_history:
        st.info(f"👋 Hi {st.session_state.first_name}! Type **Start** or **Next** to begin!")

    if prompt := st.chat_input("Type your answer or say 'Next'…"):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                response = get_gemini_model().start_chat(history=[
                    {"role": "user", "parts": [SYSTEM_PROMPT]},
                    {"role": "model", "parts": ["OK"]}
                ]).send_message(
                    f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}"
                )
                text = response.text
                st.markdown(text)
                st.session_state.conversation_history.append({"role": "assistant", "content": text})

                # STREAK & BADGE LOGIC
                first_line = text.splitlines()[0].strip().lower()
                correct = any(word in first_line for word in ["correct","yes","excellent","great job","well done","perfect","right"])
                wrong = any(word in first_line for word in ["not quite","not correct","try again","wrong"])

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
                            st.info(f"Streak ended at {st.session_state.current_streak} — awesome job well done! 💪")
                        st.session_state.current_streak = 0
                    st.session_state.question_start_time = datetime.now(TT_TZ)

# ============================================
# DASHBOARD — BIG BUTTONS & LOGIN (EXACTLY LIKE BEFORE)
# ============================================
def show_dashboard():
    st.markdown("<h1 style='text-align:center;color:#667eea;font-size:48px'>🎓 SEA Math Super-Tutor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;font-size:20px;color:#555'>Your Friendly AI Math Coach for SEA Success!</p>", unsafe_allow_html=True)

    # LOGIN
    if not st.session_state.student_name:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#f97316,#ec4899);padding:30px;border-radius:18px;text-align:center;color:white;margin:30px 0'>
            <h2>👋 Welcome, Champion!</h2>
            <p style='font-size:18px'>Enter your details to start practicing!</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2,2,1])
        with col1: first_name = st.text_input("First Name")
        with col2: last_name = st.text_input("Last Name")
        with col3: class_code = st.text_input("Class Code", type="password")

        if st.button("✅ Enter Classroom", use_container_width=True):
            if first_name and last_name and class_code:
                if class_code in st.secrets.get("class_codes", "MATH2025").split(","):
                    st.session_state.student_name = f"{first_name} {last_name}"
                    st.session_state.first_name = first_name
                    st.success(f"Welcome, {first_name}! Let's do this! 🎉")
                    st.rerun()
                else:
                    st.error("Wrong class code. Ask your teacher!")
            else:
                st.warning("Please fill everything!")
        return

    # WELCOME BACK
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#4f46e5,#0ea5e9);padding:25px;border-radius:18px;text-align:center;color:white;margin:30px 0'>
        <h2>Welcome back, {st.session_state.first_name}! 🎉</h2>
        <p style='font-size:18px'>Ready to earn some badges today?</p>
    </div>
    """, unsafe_allow_html=True)

    # VIEW PROGRESS
    if st.button("📊 View My Progress", use_container_width=True):
        with st.expander("📊 Your Progress Today", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Questions", st.session_state.questions_answered)
            with col2: st.metric("Correct", st.session_state.correct_answers)
            with col3: st.metric("Accuracy", f"{round(st.session_state.correct_answers/max(st.session_state.questions_answered,1)*100)}%")
            with col4: st.metric("🔥 Streak", st.session_state.current_streak or "—")
            if st.session_state.best_streak: st.info(f"🏆 Best Streak Ever: {st.session_state.best_streak}")

    st.markdown("<h3 style='text-align:center;color:#111827'>📚 Choose Your Topic</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔢 Number\n\nFractions • Decimals • Percentages\n34 marks on SEA!", use_container_width=True):
            st.session_state.current_topic = "Number"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()
        if st.button("📐 Geometry\n\nShapes • Angles • Symmetry\n11 marks on SEA!", use_container_width=True):
            st.session_state.current_topic = "Geometry"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()
    with c2:
        if st.button("📏 Measurement\n\nLength • Area • Time • Money\n18 marks on SEA!", use_container_width=True):
            st.session_state.current_topic = "Measurement"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()
        if st.button("📊 Statistics\n\nGraphs • Mean • Mode\n12 marks on SEA!", use_container_width=True):
            st.session_state.current_topic = "Statistics"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()

    st.markdown("<h3 style='text-align:center;color:#111827'>🎯 Special Modes</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎲 Mixed Practice\n\nAll topics — just like the real exam!", use_container_width=True):
            st.session_state.current_topic = "Mixed"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()
    with c2:
        if st.button("📝 Full SEA Practice Test\n\n40 questions • Real exam style!", use_container_width=True):
            st.session_state.current_topic = "Full Test"; st.session_state.screen = "practice"; st.session_state.conversation_history = []; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Exit", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ============================================
# RUN APP
# ============================================
if st.session_state.screen == "practice":
    show_practice_screen()
else:
    show_dashboard()
