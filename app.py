import streamlit as st
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import re
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# TIMEZONE
# ============================================
TT_TZ = ZoneInfo("America/Port_of_Spain")

def get_tt_date():
    return datetime.now(TT_TZ).date()

def now_ts():
    return datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ============================================
# CONFIG
# ============================================
GEMINI_MODEL_ID = "gemini-2.0-flash"
MAX_OUTPUT_TOKENS = 1024

# Free tier stability controls
MIN_SECONDS_BETWEEN_CALLS = 2  # debounce per session
RETRY_ON_FAIL = 0              # keep 0 on free tier to avoid doubling traffic

# ============================================
# CACHED RESOURCES
# ============================================
@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=st.secrets["google_api_key"])
    # Stateless model calls. Prompt is provided in each request for reliability.
    return genai.GenerativeModel(
        GEMINI_MODEL_ID,
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "top_p": 0.8
        }
    )

@st.cache_resource
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["google_sheets"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return gspread.authorize(creds).open("SEA_Math_Tutor_Data")
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return None

# ============================================
# SYSTEM PROMPT
# ============================================
SYSTEM_PROMPT = r"""You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.

CRITICAL IDENTITY RULES
ROLE:
- You are a friendly, encouraging AI math tutor for 11-year-olds.
- You create SEA curriculum aligned questions.
- You explain answers simply and kindly.
- You NEVER speak harshly or discourage the student.

YOU MUST NOT:
- You MUST NOT award badges.
- You MUST NOT calculate streaks.
- You MUST NOT say "you got X correct so far."
- You MUST NOT invent badge names or achievements.
- You MUST NOT reference progress.
- You MUST NOT show or mention "user:" or "assistant:" in any reply.
- You MUST NOT show the answer when asking a question.
- You MUST NOT answer your own question.
- You MUST wait for the student's answer before giving feedback.
Only the APP calculates correctness, streaks, progress, and badges.

BADGE & STREAK PROTECTION
You MUST NOT:
- Tell a student they earned a badge.
- Mention streaks.
- Say "One more for the next badge."
- Say "You are close to a badge."
- Mention bronze, silver, gold, platinum, or any badge.
- Congratulate based on progress. Only on the SINGLE answer they just gave.

QUESTION BEHAVIOR
WHEN the student says:
- "start"
- "next"
- "give me a question"
- "another"
Give ONE SEA-style question ONLY.

When asking a question:
1. Ask ONE question.
2. NEVER include the answer.
3. Keep language simple.
4. End by stating exactly:
   "This is a [Number] question."
   OR Measurement / Geometry / Statistics
   based on the topic given by the app.
5. Do NOT explain anything yet.

ANSWER FEEDBACK BEHAVIOR
When the student gives an answer:
If correct, FIRST character must be ✅
If wrong, FIRST character must be ❌

If CORRECT:
- Start with "✅ Correct!" or "✅ Yes!" or "✅ Right!" or "✅ Excellent!"
If WRONG:
- Start with "❌ Not quite." or "❌ That's not correct." or "❌ Try again."

Then:
- Give a short explanation (2 to 3 sentences).
- Teach a helpful trick.
- Ask "Want another question?"

TOPICS & CONTENT
NUMBER: whole numbers, fractions, decimals, percentages, operations
MEASUREMENT: length, area, volume, time, money, conversions
GEOMETRY: angles, symmetry, shapes, nets
STATISTICS: bar graphs, pictographs, mean, mode
Use Trinidadian examples when appropriate (doubles, maxi, Carnival, grocery).

FORMAT SUMMARY
WHEN ASKING A QUESTION:
- ONE question only.
- End with "This is a [Topic] question."

WHEN RESPONDING TO AN ANSWER:
1. ✅ or ❌ marker
2. Short explanation
3. Shortcut
4. Ask if they want another question

IMPORTANT:
- NEVER use LaTeX.
- NEVER use backslashes.
- Only write plain English and plain numbers.

ABSOLUTE RULE ABOUT TOPICS:
You will always be given a Topic:
- "Number", "Measurement", "Geometry", "Statistics", "Mixed", "Full Test"

Rules:
1. If Topic is "Number": ONLY Number questions.
2. If Topic is "Measurement": ONLY Measurement questions.
3. If Topic is "Geometry": ONLY Geometry questions.
4. If Topic is "Statistics": ONLY Statistics questions.
5. If Topic is "Mixed": you may mix all four strands.
6. If Topic is "Full Test": simulate a full SEA-style test.

At the end of each question you MUST say:
"This is a [Number] question." etc.
"""

# ============================================
# PAGE CONFIG + CSS (DARK MODE)
# ============================================
st.set_page_config(
    page_title="SEA Math Super-Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css():
    st.markdown(
        """
        <style>
        .stApp { background-color: #020617; color: #e5e7eb !important; }
        [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #020617 !important;
        }
        #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
        html, body, [class^="css"]  { color: #e5e7eb !important; }
        .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown li {
            color: #e5e7eb !important;
        }
        label, .stTextInput label, .stNumberInput label { color: #e5e7eb !important; }
        .stChatMessage[data-testid="stChatMessageUser"] {
            background-color: #111827 !important;
            border-radius: 14px;
            padding: 0.75rem 1rem;
            color: #e5e7eb !important;
        }
        .stChatMessage[data-testid="stChatMessageAssistant"] {
            background-color: #020617 !important;
            border-radius: 14px;
            padding: 0.75rem 1rem;
            color: #e5e7eb !important;
        }
        [data-testid="stChatMessage"] > div:first-child {display: none !important;}
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
        ::placeholder { color: #6b7280 !important; }
        [data-testid="metric-container"] {
            background-color: #020617 !important;
            border-radius: 12px;
            padding: 0.75rem;
            border: 1px solid #1f2937;
        }
        [data-testid="metric-container"] label, [data-testid="metric-container"] span {
            color: #e5e7eb !important;
        }
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
        div[data-testid="column"] > div > div > button {
            min-height: 120px;
            white-space: pre-wrap;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

load_css()

# ============================================
# SESSION STATE
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

st.session_state.setdefault("daily_date", None)
st.session_state.setdefault("daily_count", 0)

# Generation + debug + rate controls
st.session_state.setdefault("is_generating", False)
st.session_state.setdefault("last_gemini_error", None)
st.session_state.setdefault("cooldown_until", 0.0)
st.session_state.setdefault("last_request_time", 0.0)

# Stateless support
st.session_state.setdefault("last_question_text", None)

def show_debug_enabled():
    return str(st.secrets.get("show_debug", "false")).lower() == "true"

# ============================================
# RATE LIMIT HELPERS
# ============================================
def parse_retry_seconds(err_text: str) -> int:
    m = re.search(r"retry in\s+([\d.]+)s", err_text, re.IGNORECASE)
    if not m:
        return 30
    return max(1, int(float(m.group(1)) + 1))

def is_rate_limited(err_text: str) -> bool:
    t = err_text.lower()
    return (
        "resourceexhausted" in t
        or "quota exceeded" in t
        or "rate limit" in t
        or "429" in t
    )

# ============================================
# SHEETS + BADGES
# ============================================
def get_or_create_student_id(name: str):
    base_id = f"STU{abs(hash(name))}"[:10]
    try:
        sheet = get_sheets_client()
        if not sheet:
            return base_id

        ws = sheet.worksheet("Students")
        names_col = ws.col_values(2)  # column B

        for i, n in enumerate(names_col, 1):
            if n.strip().lower() == name.strip().lower():
                existing_id = ws.cell(i, 1).value
                return existing_id if existing_id else base_id

        ws.append_row([base_id, name, now_ts()])
        return base_id
    except Exception:
        return base_id

def log_student_activity(sid, name, qtype, strand, correct, secs):
    try:
        sheet = get_sheets_client()
        if sheet:
            sheet.worksheet("Activity_Log").append_row(
                [now_ts(), sid, name, qtype, strand, "Yes" if correct else "No", secs]
            )
    except Exception:
        pass

def log_badge_award(student_id, name, badge_name):
    try:
        sheet = get_sheets_client()
        if sheet:
            sheet.worksheet("Badges").append_row([name, badge_name, now_ts()])
    except Exception:
        pass

def award_badge(streak):
    name = st.session_state.first_name.split()[0] if st.session_state.first_name else "Champion"
    full_name = st.session_state.student_name or name
    student_id = st.session_state.student_id

    badge_name = None
    if streak == 5:
        badge_name = "BRONZE STAR"
        st.balloons()
        st.success(f"🎖️ **BRONZE STAR** - {name}, 5 in a row! Keep shining! ✨")
    elif streak == 10:
        badge_name = "SILVER TROPHY"
        st.snow()
        st.success(f"🏆 **SILVER TROPHY** - {name} hits 10 perfect! Unstoppable! 🚀")
    elif streak == 15:
        badge_name = "GOLD MEDAL"
        st.balloons()
        st.success(f"🥇 **GOLD MEDAL** - {name} scores 15 in a row! Champion! 🏆")
    elif streak == 20:
        badge_name = "PLATINUM CROWN"
        st.snow()
        st.balloons()
        st.success(f"👑 **PLATINUM CROWN** - {name} reaches 20! You're royalty! 👑")
    elif streak == 25:
        badge_name = "DIAMOND LEGEND"
        st.snow()
        st.balloons()
        st.toast("💎 DIAMOND LEGEND UNLOCKED!", icon="💎")
        st.success(f"💎 **DIAMOND LEGEND** - {name} got 25 in a row! SEA HISTORY! 🌟")

    if badge_name:
        log_badge_award(student_id, full_name, badge_name)

# ============================================
# DAILY LIMIT
# ============================================
def check_daily_limit():
    limit = int(st.secrets.get("daily_limit_per_student", 50))
    today = get_tt_date().isoformat()
    if st.session_state.get("daily_date") != today:
        st.session_state.daily_date = today
        st.session_state.daily_count = 0
    if st.session_state.daily_count >= limit:
        st.warning("Daily limit reached! Come back tomorrow! 🎉")
        st.stop()

# ============================================
# DETECT CORRECTNESS
# ============================================
def detect_correctness(text: str):
    """
    Primary check: leading emoji (✅ ✓ 🎉 = correct, ❌ = wrong).
    Fallback: phrase scan for safety in case Gemini omits the emoji.
    """
    first_line = text.splitlines()[0].strip() if text else ""

    # Primary: emoji markers
    if first_line.startswith("✅") or first_line.startswith("✓") or first_line.startswith("🎉"):
        return True, True
    if first_line.startswith("❌"):
        return True, False

    # Fallback: phrase scan (safety net only)
    lower = first_line.lower()
    CORRECT_PHRASES = ["correct", "right!", "excellent", "well done", "you got it"]
    WRONG_PHRASES   = ["not quite", "that's not correct", "try again", "good try, but"]
    for p in CORRECT_PHRASES:
        if lower.startswith(p):
            return True, True
    for p in WRONG_PHRASES:
        if lower.startswith(p):
            return True, False

    return False, False

# ============================================
# STATELESS GEMINI CALL
# ============================================
def build_payload(student_text: str) -> str:
    """
    Builds a compact payload. System prompt is passed once via system_instruction
    at model init — NOT repeated here, which would burn free-tier token quota fast.
    """
    topic = st.session_state.current_topic
    first_name = st.session_state.first_name or "Student"
    last_q = st.session_state.last_question_text

    normalized = (student_text or "").strip().lower()
    is_request = normalized in {"start", "next", "another", "give me a question"}

    if is_request:
        return (
            f"TASK: ASK_ONE_QUESTION\n"
            f"Topic: {topic}\n"
            f"Student first name: {first_name}\n"
            f"Give ONE question only. End with: This is a {topic} question."
        )

    if not last_q:
        return (
            f"TASK: ASK_ONE_QUESTION\n"
            f"Topic: {topic}\n"
            f"Student first name: {first_name}\n"
            f"No previous question available. Ask ONE question only. End with: This is a {topic} question."
        )

    return (
        f"TASK: GRADE_STUDENT_ANSWER\n"
        f"Topic: {topic}\n"
        f"Student first name: {first_name}\n"
        f"Previous question: {last_q}\n"
        f"Student answer: {student_text}\n"
        f"Start with ✅ if correct or ❌ if wrong. Explain briefly in 2-3 sentences. "
        f"Do NOT ask a new question."
    )

def safe_generate(student_text: str) -> str:
    now = time.time()

    # Cooldown gate
    if now < st.session_state.cooldown_until:
        remaining = int(st.session_state.cooldown_until - now)
        raise RuntimeError(f"COOLDOWN_ACTIVE:{remaining}")

    # Debounce gate
    if now - st.session_state.last_request_time < MIN_SECONDS_BETWEEN_CALLS:
        raise RuntimeError("TOO_FAST")

    if st.session_state.is_generating:
        raise RuntimeError("ALREADY_GENERATING")

    st.session_state.is_generating = True
    st.session_state.last_gemini_error = None

    try:
        model = get_gemini_model()
        payload = build_payload(student_text)

        # Single attempt on free tier (RETRY_ON_FAIL=1 enables one retry)
        attempts = 1 + max(0, int(RETRY_ON_FAIL))
        last_err = None

        for attempt in range(attempts):
            try:
                resp = model.generate_content(payload)
                text = getattr(resp, "text", None)
                if text and text.strip():
                    return text.strip()
                raise RuntimeError("EMPTY_RESPONSE")
            except Exception as e:
                last_err = e
                err_text = repr(e)
                if is_rate_limited(err_text):
                    wait_s = parse_retry_seconds(err_text)
                    st.session_state.cooldown_until = time.time() + wait_s
                    raise RuntimeError(f"RATE_LIMIT:{wait_s}")
                if attempt < attempts - 1:
                    time.sleep(1.0)
                    continue
        raise last_err
    finally:
        st.session_state.is_generating = False
        st.session_state.last_request_time = time.time()  # FIX 5: update debounce timer

def update_last_question_if_needed(assistant_text: str):
    is_feedback, _ = detect_correctness(assistant_text)
    if not is_feedback and assistant_text and assistant_text.strip():
        st.session_state.last_question_text = assistant_text.strip()

# ============================================
# UI SCREENS
# ============================================
def show_dashboard():
    st.markdown("<h1 style='text-align:center;color:#a5b4fc'>🎓 SEA Math Super-Tutor</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#e5e7eb;font-size:20px'>Your Friendly AI Math Coach for SEA Success!</p>",
        unsafe_allow_html=True
    )

    if show_debug_enabled():
        with st.expander("Developer Debug", expanded=False):
            st.write("Model:", GEMINI_MODEL_ID)
            if st.session_state.get("last_gemini_error"):
                st.code(st.session_state["last_gemini_error"])
            cd = st.session_state.get("cooldown_until", 0.0)
            if cd and time.time() < cd:
                st.write("Cooldown remaining (s):", int(cd - time.time()))
            st.write("Last question stored:", bool(st.session_state.get("last_question_text")))

    if not st.session_state.student_name:
        st.markdown(
            """
            <div style='background:linear-gradient(135deg,#f97316,#ec4899);
                        padding:30px;border-radius:18px;text-align:center;color:white'>
                <h2>👋 Welcome, Champion!</h2>
                <p>Enter your details to start!</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            first = st.text_input("First Name")
        with col2:
            last = st.text_input("Last Name")
        with col3:
            code = st.text_input("Class Code", type="password")

        if st.button("✅ Enter"):
            allowed_codes = st.secrets.get("class_codes", "MATH2025").split(",")
            allowed_codes = [c.strip() for c in allowed_codes if c.strip()]
            if first and last and code in allowed_codes:
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
                st.session_state.last_question_text = None
                st.session_state.last_gemini_error = None
                st.session_state.cooldown_until = 0.0
                st.session_state.last_request_time = 0.0
                st.rerun()

def show_practice_screen():
    check_daily_limit()

    icons = {
        "Number": "🔢",
        "Measurement": "📏",
        "Geometry": "📐",
        "Statistics": "📊",
        "Mixed": "🎲",
        "Full Test": "📝"
    }

    col1, col2 = st.columns([5, 1])
    with col1:
        st.title(f"{icons[st.session_state.current_topic]} {st.session_state.current_topic} Practice")
    with col2:
        if st.button("🚪 Exit"):
            st.session_state.screen = "dashboard"
            st.rerun()

    cd = st.session_state.get("cooldown_until", 0.0)
    now = time.time()
    if cd and now < cd:
        st.info(f"Quick break: {int(cd - now)} seconds left 😊")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Questions", st.session_state.questions_answered)
    with c2:
        st.metric("Correct", st.session_state.correct_answers)
    with c3:
        acc = round(st.session_state.correct_answers / max(st.session_state.questions_answered, 1) * 100)
        st.metric("Accuracy", f"{acc}%")
    with c4:
        st.metric("🔥 Streak", st.session_state.current_streak)

    st.write("---")

    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    if not st.session_state.conversation_history:
        st.info(f"👋 Hi {st.session_state.first_name}! Type **Start** to begin!")

    prompt = st.chat_input("Type your answer or say 'Next'...")
    if not prompt:
        return

    st.session_state.conversation_history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            try:
                text = safe_generate(prompt)
            except Exception as e:
                st.session_state.last_gemini_error = repr(e)
                msg = str(e)

                if msg.startswith("RATE_LIMIT:"):
                    wait_s = msg.split(":")[1]
                    text = f"Quick break. Please wait about {wait_s} seconds, then type Next. 😊"
                elif msg.startswith("COOLDOWN_ACTIVE:"):
                    remaining = msg.split(":")[1]
                    text = f"Please wait {remaining} seconds, then type Next. 😊"
                elif msg == "TOO_FAST":
                    text = "Let's go one step at a time 😊"
                elif msg == "ALREADY_GENERATING":
                    text = "One moment please 😊"
                else:
                    text = f"Connection problem: {repr(e)} — please type Next to try again."

            st.markdown(text)
            st.session_state.conversation_history.append({"role": "assistant", "content": text})

            update_last_question_if_needed(text)

            is_feedback, correct = detect_correctness(text)

            if not is_feedback:
                st.session_state.question_start_time = datetime.now(TT_TZ)

            if is_feedback:
                st.session_state.questions_answered += 1
                st.session_state.daily_count += 1

                if correct:
                    st.session_state.correct_answers += 1
                    st.session_state.current_streak += 1
                    st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.current_streak)
                    if st.session_state.current_streak in [5, 10, 15, 20, 25]:
                        award_badge(st.session_state.current_streak)
                else:
                    if st.session_state.current_streak >= 5:
                        st.info(f"Streak ended at {st.session_state.current_streak}. Great job!")
                    st.session_state.current_streak = 0

                elapsed = int((datetime.now(TT_TZ) - st.session_state.question_start_time).total_seconds())
                log_student_activity(
                    st.session_state.student_id,
                    st.session_state.student_name,
                    "Question",
                    st.session_state.current_topic,
                    correct,
                    elapsed
                )

# ============================================
# MAIN
# ============================================
if st.session_state.screen == "practice":
    show_practice_screen()
else:
    show_dashboard()
