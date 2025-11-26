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
# SYSTEM PROMPT (your full original)
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
WHEN the student says:
- “start”
- “next”
- “give me a question”
- “another”
→ Give ONE SEA-style question ONLY.
When asking a question:
1. Ask ONE question.
2. NEVER include the answer.
3. Keep language simple.
4. End by stating:
   “This is a [Number] question.”
   OR Measurement / Geometry / Statistics
   (based on the topic given by the app)
5. Do NOT explain anything yet.
============================================================
ANSWER FEEDBACK BEHAVIOR
============================================================
When the student gives an answer:
FIRST LINE IF CORRECT:
- “✅ Correct!”
- “🎉 Yes! Correct!”
- “✓ Right!”
- “Excellent work!”
- “You got it!”
FIRST LINE IF WRONG:
- “❌ Not quite.”
- “That's not correct.”
- “Good try, but not correct.”
- “Almost, but not quite.”
Then:
- Give a short explanation (2–3 sentences maximum).
- Teach a helpful trick or shortcut.
- Ask “Want another question?”
Do NOT:
- Reference streaks
- Mention badges
- Mention progress
- Compare to earlier questions
- Say “Four in a row!” or any number
============================================================
TOPICS & CONTENT
============================================================
NUMBER (34 marks): whole numbers, fractions, decimals, percentages, operations
MEASUREMENT (18 marks): length, area, volume, time, money, conversions
GEOMETRY (11 marks): angles, symmetry, shapes, nets
STATISTICS (12 marks): bar graphs, pictographs, mean, mode
Use Trinidadian examples when appropriate (doubles, maxi, Carnival, grocery, etc.)
Keep explanations warm, short, encouraging.
Use emojis where appropriate.
============================================================
FORMAT SUMMARY
============================================================
WHEN ASKING A QUESTION:
- ONE question only.
- End with “This is a [Topic] question.”
WHEN RESPONDING TO AN ANSWER:
1. Correct/Not Correct marker
2. Short explanation
3. Shortcut
4. Ask if they want another question
NEVER:
- Award badges
- Count streaks
- Mention progress
- Predict or guess correctness history
- Pretend to be the student
- Use “user:” or “assistant:”
YOUR ROLE:
- IMPORTANT: NEVER use LaTeX, never use backslashes, never wrap anything in $…$, and never write equations like \frac or \mathbf. Only write plain English text and plain numbers.
- Create SEA-standard questions based on the official SEA framework.
- Test: Number (34 marks), Measurement (18 marks), Geometry (11 marks), Statistics (12 marks).
- Use 11-year-old friendly language.
- Give ONE question at a time.
- After they answer, tell if correct and explain.
- Teach shortcuts and hacks.
ABSOLUTE RULE ABOUT TOPICS (DO NOT DISOBEY):
You will always be given a Topic, which is one of:
- "Number"
- "Measurement"
- "Geometry"
- "Statistics"
- "Mixed"
- "Full Test"
You MUST follow these rules:
1. If Topic is "Number": EVERY question must be ONLY a Number question.
2. If Topic is "Measurement": EVERY question must be ONLY a Measurement question.
3. If Topic is "Geometry": EVERY question must be ONLY a Geometry question.
4. If Topic is "Statistics": EVERY question must be ONLY a Statistics question.
5. If Topic is "Mixed": You may mix all four strands.
6. If Topic is "Full Test": Simulate a full SEA-style test.
At the end of each question you MUST clearly say:
- "This is a [Number] question." etc.
CRITICAL - ANSWER FEEDBACK FORMAT:
When student answers, you MUST start your response with one of these:
- If CORRECT: Start with "✅ Correct!" or "🎉 Yes!" or "✓ Right!" or "Excellent!"
- If WRONG: Start with "❌ Not quite" or "That's not correct" or "Try again"
This is VERY IMPORTANT for tracking their progress!
You are helping them become math champions! 🏆
"""

# ============================================
# PAGE CONFIG + CSS
# ============================================
st.set_page_config(page_title="SEA Math Super-Tutor", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

def load_css():
    st.markdown("""
    <style>
    /* Global app background & text */
    .stApp {
        background-color: #020617; /* very dark navy */
        color: #e5e7eb !important;  /* light gray text */
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] {
        background-color: #020617 !important;
    }
    [data-testid="stHeader"] {
        background-color: #020617 !important;
    }

    /* Hide default chrome */
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}

    /* Typography overrides */
    html, body, [class^="css"]  {
        color: #e5e7eb !important;
    }
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {
        color: #e5e7eb !important;
    }
    label, .stTextInput label, .stNumberInput label {
        color: #e5e7eb !important;
    }

    /* Chat messages */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #111827 !important; /* slate-900 */
        border-radius: 14px;
        padding: 0.75rem 1rem;
        color: #e5e7eb !important;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #020617 !important; /* slightly different dark */
        border-radius: 14px;
        padding: 0.75rem 1rem;
        color: #e5e7eb !important;
    }
    .stChatMessage .stMarkdown p {
        color: #e5e7eb !important;
    }
    /* Hide role labels */
    [data-testid="stChatMessage"] > div:first-child {display: none !important;}

    /* Inputs (text fields, password, etc.) */
    input, textarea {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-color: #374151 !important;
    }
    input:focus, textarea:focus {
        outline: none !important;
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }
    ::placeholder {
        color: #6b7280 !important;
    }

    /* Chat input box */
    [data-testid="stChatInput"] textarea {
        background-color: #020617 !important;
        color: #e5e7eb !important;
    }

    /* Metrics panels */
    [data-testid="metric-container"] {
        background-color: #020617 !important;
        border-radius: 12px;
        padding: 0.75rem;
        border: 1px solid #1f2937;
    }
    [data-testid="metric-container"] label,
    [data-testid="metric-container"] span {
        color: #e5e7eb !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 14px;
        font-weight: 700;
        border: none;
        padding: 0.85rem 1.1rem;
        font-size: 1.05rem;
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5, #6366f1);
        box-shadow: 0 4px 10px rgba(15,23,42,0.6);
    }
    .stButton > button:hover {
        box-shadow: 0 6px 14px rgba(15,23,42,0.9);
        opacity: 0.95;
    }

    /* Topic buttons in columns */
    div[data-testid="column"] > div > div > button {
        min-height: 120px;
        white-space: pre-wrap;
    }

    /* Info / success / warning boxes */
    .stAlert {
        background-color: #0f172a !important;
        color: #e5e7eb !important;
    }
    .stAlert p {
        color: #e5e7eb !important;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

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
# BADGE SYSTEM
# ============================================
def award_badge(streak):
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
        st.balloons()
        st.toast("💎 DIAMOND LEGEND UNLOCKED!", icon="💎")
        st.success(f"💎 **DIAMOND LEGEND** – {name} got 25 in a row! SEA HISTORY! 🌟")

# ============================================
# HELPER FUNCTIONS
# ============================================
def get_or_create_student_id(name):
    base = f"STU{abs(hash(name))}"[:10]
    try:
        sheet = get_sheets_client()
        if sheet:
            students = sheet.worksheet("Students").col_values(2)
            for i, n in enumerate(students, 1):
                if n.strip().lower() == name.strip().lower():
                    return sheet.worksheet("Students").cell(i, 1).value or base
        return base
    except:
        return base

def log_student_activity(sid, name, qtype, strand, correct, secs):
    ts = datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    try:
        get_sheets_client().worksheet("Activity_Log").append_row([ts, sid, name, qtype, strand, "Yes" if correct else "No", secs])
    except:
        pass

def check_daily_limit():
    limit = int(st.secrets.get("daily_limit_per_student", 50))
    today = get_tt_date().isoformat()
    if st.session_state.get("daily_date") != today:
        st.session_state.daily_date = today
        st.session_state.daily_count = 0
    if st.session_state.daily_count >= limit:
        st.warning("Daily limit reached! Come back tomorrow! 🎉")
        st.stop()

def get_or_create_chat():
    if "gemini_chat" not in st.session_state:
        model = get_gemini_model()
        st.session_state.gemini_chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood!"]}
        ])
    return st.session_state.gemini_chat

# ============================================
# DASHBOARD
# ============================================
def show_dashboard():
    st.markdown("<h1 style='text-align:center;color:#a5b4fc'>🎓 SEA Math Super-Tutor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#e5e7eb;font-size:20px'>Your Friendly AI Math Coach for SEA Success!</p>", unsafe_allow_html=True)

    if not st.session_state.student_name:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#f97316,#ec4899);
                    padding:30px;border-radius:18px;text-align:center;color:white'>
            <h2>👋 Welcome, Champion!</h2>
            <p>Enter your details to start!</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: first = st.text_input("First Name")
        with col2: last = st.text_input("Last Name")
        with col3: code = st.text_input("Class Code", type="password")
        if st.button("✅ Enter"):
            if first and last and code in st.secrets.get("class_codes", "MATH2025").split(","):
                name = f"{first} {last}"
                st.session_state.student_name = name
                st.session_state.first_name = first
                st.session_state.student_id = get_or_create_student_id(name)
                st.rerun()
            else:
                st.error("Check your details!")
        return

    st.success(f"Welcome back, {st.session_state.first_name}! 🎉")

    if st.button("📊 View Progress"):
        with st.expander("Your Progress Today", expanded=True):
            st.metric("Streak", st.session_state.current_streak)
            st.metric("Best Streak", st.session_state.best_streak)

    col1, col2 = st.columns(2)
    topics = ["Number", "Measurement", "Geometry", "Statistics", "Mixed", "Full Test"]
    icons = ["🔢", "📏", "📐", "📊", "🎲", "📝"]
    for i, topic in enumerate(topics):
        with col1 if i % 2 == 0 else col2:
            if st.button(f"{icons[i]} {topic}", use_container_width=True):
                st.session_state.current_topic = topic
                st.session_state.screen = "practice"
                st.session_state.conversation_history = []
                st.rerun()

# ============================================
# PRACTICE SCREEN (FIXED + BADGES)
# ============================================
def show_practice_screen():
    check_daily_limit()

    col1, col2 = st.columns([5,1])
    with col1:
        icons = {"Number":"🔢","Measurement":"📏","Geometry":"📐","Statistics":"📊","Mixed":"🎲","Full Test":"📝"}
        st.title(f"{icons[st.session_state.current_topic]} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("🚪 Exit"):
            st.session_state.screen = "dashboard"
            st.rerun()

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Questions", st.session_state.questions_answered)
    with c2: st.metric("Correct", st.session_state.correct_answers)
    with c3: st.metric("Accuracy", f"{round(st.session_state.correct_answers/max(st.session_state.questions_answered,1)*100)}%")
    with c4: st.metric("🔥 Streak", st.session_state.current_streak)

    st.write("---")

    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
            st.markdown(msg["content"])

    if not st.session_state.conversation_history:
        st.info(f"👋 Hi {st.session_state.first_name}! Type **Start** to begin!")

    if prompt := st.chat_input("Type your answer or say 'Next'…"):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)

        chat = get_or_create_chat()
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                try:
                    response = chat.send_message(f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\n\n{prompt}")
                    text = response.text
                except:
                    text = "Let’s try another question! 😊"

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
                            award_badge(st.session_state.current_streak)
                    else:
                        if st.session_state.current_streak >= 5:
                            st.info(f"Streak ended at {st.session_state.current_streak} — great job!")
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
