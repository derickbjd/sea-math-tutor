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
        creds = Credentials.from_service_account_info(
            st.secrets["google_sheets"],
            scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds).open("SEA_Math_Tutor_Data")
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return None

# ============================================
# FULL SYSTEM PROMPT (COMPLETE & CLOSED!)
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
============================================================
BADGE & STREAK PROTECTION (CRITICAL)
============================================================
You MUST NOT:
- Tell a student they earned a badge.
- Mention streaks (“You have 4 in a row”).
- Say “One more for the next badge.”
- Say “You are close to a badge.”
- Mention bronze, silver, gold, platinum, or any badge.
- Congratulate based on progress — only on the SINGLE answer they just gave.
============================================================
QUESTION BEHAVIOR
============================================================
WHEN the student says “start”, “next”, “give me a question”, “another” → Give ONE SEA-style question ONLY.
When asking a question:
1. Ask ONE question.
2. NEVER include the answer.
3. End with: “This is a [Number] question.” (or Measurement/Geometry/Statistics based on topic)
============================================================
ANSWER FEEDBACK BEHAVIOR
============================================================
When student answers:
- If CORRECT: First line must be “✅ Correct!” or “🎉 Yes!” or “Excellent!”
- If WRONG: First line must be “❌ Not quite” or “That's not correct”
Then: short explanation + tip + “Want another question?”
NEVER mention streaks or badges.
You are helping them become math champions! 🏆"""

# ============================================
# PAGE CONFIG + CSS (Progress visible!)
# ============================================
st.set_page_config(page_title="SEA Math Super-Tutor", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

def load_css():
    st.markdown("""
    <style>
    .stApp {background-color: #f5f7fb;}
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    .stChatMessage .stMarkdown p {color: #111827 !important;}
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
    .stExpander > div > label, .stExpander .stMarkdown {color: #111827 !important; font-weight: 600;}
    </style>
    """, unsafe_allow_html=True)
load_css()

# ============================================
# SESSION STATE + STREAK
# ============================================
for key, value in {
    "screen": "dashboard", "student_name": None, "first_name": None, "student_id": None,
    "current_topic": None, "questions_answered": 0, "correct_answers": 0,
    "current_streak": 0, "best_streak": 0, "session_start": None,
    "conversation_history": [], "question_start_time": datetime.now(TT_TZ),
    "daily_usage": {"date": get_tt_date().isoformat(), "count": 0}, "pending_logs": []
}.items():
    st.session_state.setdefault(key, value)

# ============================================
# BADGE SYSTEM
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
# LOGGING
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

# ============================================
# CHAT
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
# PRACTICE SCREEN
# ============================================
def show_practice_screen():
    col1, col2 = st.columns([5,1])
    with col1:
        icons = {"Number":"🔢","Measurement":"📏","Geometry":"📐","Statistics":"📊","Mixed":"🎲","Full Test":"📝"}
        st.title(f"{icons.get(st.session_state.current_topic,'📚')} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("🚪 Exit"):
            st.session_state.screen = "dashboard"
            st.rerun()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Questions", st.session_state.questions_answered)
    with c2: st.metric("Correct", st.session_state.correct_answers)
    with c3: st.metric("Accuracy", f"{round(st.session_state.correct_answers/max(st.session_state.questions_answered,1)*100)}%")
    with c4: st.metric("🔥 Streak", st.session_state.current_streak if st.session_state.current_streak else "—")

    st.write("---")

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
                resp = get_or_create_chat().send_message(
                    f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}"
                )
                text = resp.text
                st.markdown(text)
                st.session_state.conversation_history.append({"role": "assistant", "content": text})

                first = text.splitlines()[0].strip().lower()
                correct = any(x in first for x in ["correct","yes!","excellent","great job","well done","perfect","right","you got it"])
                wrong = any(x in first for x in ["not quite","not correct","try again","wrong","almost"])

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
# DASHBOARD
# ============================================
def show_dashboard():
    st.markdown("<h1 style='text-align:center;color:#667eea'>🎓 SEA Math Super-Tutor</h1>", unsafe_allow_html=True)

    if not st.session_state.student_name:
        col1, col2, col3 = st.columns(3)
        with col1: first = st.text_input("First Name")
        with col2: last = st.text_input("Last Name")
        with col3: code = st.text_input("Class Code", type="password")
        if st.button("Enter"):
            if first and last and code == "MATH2025":
                st.session_state.student_name = f"{first} {last}"
                st.session_state.first_name = first
                st.session_state.student_id = f"STU{hash(first+last)%10000}"
                st.rerun()
        return

    st.success(f"Welcome back, {st.session_state.first_name}! 🎉")

    if st.button("📊 View Progress"):
        with st.expander("Your Progress", expanded=True):
            st.metric("Streak", st.session_state.current_streak)
            st.metric("Best Streak", st.session_state.best_streak)

    col1, col2 = st.columns(2)
    topics = ["Number", "Measurement", "Geometry", "Statistics", "Mixed", "Full Test"]
    icons = ["🔢", "📏", "📐", "📊", "🎲", "📝"]
    for i, topic in enumerate(topics):
        with col1 if i % 2 == 0 else col2:
            if st.button(f"{icons[i]} {topic}"):
                st.session_state.current_topic = topic
                st.session_state.screen = "practice"
                st.session_state.conversation_history = []
                st.rerun()

# ============================================
# MAIN
# ============================================
if st.session_state.screen == "practice":
    show_practice_screen()
else:
    show_dashboard()
