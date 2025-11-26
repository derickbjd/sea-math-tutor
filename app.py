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
    """Return today's date in Trinidad & Tobago timezone."""
    return datetime.now(TT_TZ).date()

# ============================================
# CACHED RESOURCES (HUGE SPEED + COST WIN)
# ============================================
@st.cache_resource
def get_gemini_model():
    """Configure Google Gemini AI with safety config."""
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
    """Connect to Google Sheets using cached client."""
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

# ============================================
# SYSTEM PROMPT (global constant – MASSIVE token saver!)
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
1. If Topic is "Number":
   - EVERY question must be ONLY a Number question.
   - Examples: whole numbers, fractions, decimals, percentages, ratios, patterns.
   - DO NOT ask Measurement, Geometry, or Statistics questions.
2. If Topic is "Measurement":
   - EVERY question must be ONLY a Measurement question.
   - Examples: length, area, perimeter, volume, mass, time, money.
   - DO NOT ask Number, Geometry, or Statistics questions.
3. If Topic is "Geometry":
   - EVERY question must be ONLY a Geometry question.
   - Examples: shapes, symmetry, angles, lines, perpendicular/parallel, properties of shapes.
   - DO NOT ask Number, Measurement, or Statistics questions.
4. If Topic is "Statistics":
   - EVERY question must be ONLY a Statistics question.
   - Examples: bar graphs, pictographs, tables, tally charts, mean, mode, interpreting data.
   - DO NOT ask Number, Measurement, or Geometry questions.
5. If Topic is "Mixed":
   - You may mix all four strands (Number, Measurement, Geometry, Statistics).
   - Vary the strands across questions like a real mixed practice.
6. If Topic is "Full Test":
   - Simulate a full SEA-style test, drawing from all strands.
   - Balance roughly like SEA: more Number; fewer Geometry and Statistics.
   - Still only send ONE question at a time, but choose strands across the whole paper.
   - Keep timing/exam language in mind, but the app will handle the actual timer.
At the end of each question you MUST clearly say:
- "This is a [Number] question."
- OR "This is a [Measurement] question."
- OR "This is a [Geometry] question."
- OR "This is a [Statistics] question."
This must ALWAYS match the actual topic/strand of the question and obey the Topic rules above.
CRITICAL - ANSWER FEEDBACK FORMAT:
When student answers, you MUST start your response with one of these:
- If CORRECT: Start with "✅ Correct!" or "🎉 Yes!" or "✓ Right!" or "Excellent!"
- If WRONG: Start with "❌ Not quite" or "That's not correct" or "Try again"
This is VERY IMPORTANT for tracking their progress!
QUESTION TYPES BY STRAND:
NUMBER: Whole numbers, fractions, decimals, percentages, ratios, patterns.
MEASUREMENT: Length, area, perimeter, volume, mass, time, money.
GEOMETRY: Shapes, symmetry, angles, lines, properties of shapes.
STATISTICS: Graphs, tables, tally charts, mean, mode, interpreting data.
TEACHING STYLE:
- Simple, clear language.
- Use Trinidad & Tobago examples when possible (doubles, roti, maxi rides, etc.).
- Celebrate wins: "Yes! 🎉 Well done!"
- When wrong: explain kindly, show method, give a shortcut/hack.
- Use analogies that an 11-year-old in Trinidad would understand.
HACKS TO TEACH:
- Divide by 25: Multiply by 4, then divide by 100.
- Multiply by 5: Multiply by 10, then divide by 2.
- Find 10%: Move decimal one place to the left.
- Perimeter of rectangle: (Length + Width) × 2.
- Mean: Add all, divide by how many numbers.
- Mode: The number that appears the most.
FORMAT OF YOUR RESPONSES:
1. If the student says "start", "next", or asks for a question:
   - Give ONE question only.
   - Clearly say at the end: "This is a [Number/Measurement/Geometry/Statistics] question."
   - Obey the Topic rules above.
2. If the student gives an answer:
   - FIRST LINE: "✅ Correct!" OR "❌ Not quite" (or equivalent from the lists above).
   - Then explain why the answer is right or wrong in simple steps.
   - Then teach a small hack/tip.
   - Then ask if they want another question.
3. Keep responses short (2–3 short paragraphs).
4. Use emojis to keep it fun (🎉, ✅, ❌, 📊, 📏, 🔢, 📐).
5. Remember: you are a kind, patient SEA coach helping them build confidence, not just score marks.
EXAMPLE GOOD RESPONSES:
"✅ Correct! You got it, Marcus! The answer is 46 m. Here's why: The perimeter is all the way around..."
"❌ Not quite, but good try! The answer is actually 46 m, not 23 m. Here's what happened..."
You are helping them become math champions! 🏆
"""

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="SEA Math Super-Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS
# ============================================
def load_css():
    st.markdown(
        """
    <style>
    /* ===== Global page styling ===== */
    .stApp {
        background-color: #f5f7fb; /* soft light grey/blue */
    }
    /* FIX: Make AI-generated tables readable */
table, th, td {
    color: #111827 !important; /* dark text */
    border-color: #9ca3af !important; /* soft grey border */
}
thead th {
    background-color: #e5e7eb !important; /* light grey header */
    color: #111827 !important;
}
tbody td {
    background-color: #ffffff !important; /* white cells */
}
    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    /* ===== Chat text visibility (fix white-on-white) ===== */
    .stChatMessage .stMarkdown p,
    .stChatMessage .stMarkdown li,
    .stChatMessage .stMarkdown span {
        color: #111827 !important; /* dark grey text */
    }
    /* Hide Streamlit's "user" / "assistant" chat labels */
    [data-testid="stChatMessage"] > div:first-child {
        display: none !important;
    }
    /* User vs assistant bubbles */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #e0f2fe !important; /* light blue */
        border-radius: 14px;
        padding: 0.75rem 1rem;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #ffffff !important;
        border-radius: 14px;
        padding: 0.75rem 1rem;
    }
    /* ===== Buttons – colourful, readable, kid-friendly ===== */
    /* Base style for ALL buttons */
    .stButton > button {
        border-radius: 14px;
        font-weight: 700;
        border: none;
        padding: 0.85rem 1.1rem;
        font-size: 1.05rem;
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5, #6366f1); /* default indigo gradient */
        box-shadow: 0 4px 10px rgba(79, 70, 229, 0.25);
        transition: transform 0.1s ease, box-shadow 0.1s ease, filter 0.1s ease;
        text-align: left;
    }
    /* Hover state */
    .stButton > button:hover {
        filter: brightness(1.05);
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(79, 70, 229, 0.35);
    }
    /* Active / focused state – keep text visible */
    .stButton > button:active,
    .stButton > button:focus {
        outline: none !important;
        border: none !important;
        background: linear-gradient(135deg, #4338ca, #4f46e5);
        color: #ffffff !important;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.35);
        transform: translateY(0);
    }
    /* Make emojis/icons feel bigger & fun for 11-year-olds */
    .stButton > button p,
    .stButton > button span {
        font-size: 1.15rem;
        line-height: 1.3;
    }
    /* Topic buttons inside columns – give them more height like cards */
    div[data-testid="column"] > div > div > button {
        min-height: 120px;
        white-space: pre-wrap;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

load_css()

# ============================================
# SESSION STATE INITIALIZATION (cleaner with setdefault)
# ============================================
st.session_state.setdefault("screen", "dashboard")
st.session_state.setdefault("student_name", None)
st.session_state.setdefault("student_id", None)
st.session_state.setdefault("first_name", None)
st.session_state.setdefault("current_topic", None)
st.session_state.setdefault("questions_answered", 0)
st.session_state.setdefault("correct_answers", 0)
st.session_state.setdefault("session_start", None)
st.session_state.setdefault("conversation_history", [])
today = get_tt_date().isoformat()
st.session_state.setdefault("daily_usage", {"date": today, "count": 0})
st.session_state.setdefault("badge_progress", {
    "number": 0,
    "measurement": 0,
    "geometry": 0,
    "statistics": 0,
})
st.session_state.setdefault("pending_logs", [])  # NEW: for batching

# ============================================
# GOOGLE SHEETS CONNECTION (optimized with batching)
# ============================================
def get_or_create_student_id(student_name: str) -> str:
    """
    Return an existing Student_ID for this student_name if it exists in the
    'Students' worksheet. Otherwise, create a deterministic new one based
    only on the name so it stays stable across sessions.
    """
    base_id = f"STU{abs(hash(student_name))}".replace("-", "")[:10]
    try:
        sheet = get_sheets_client()
        if not sheet:
            return base_id
        students_sheet = sheet.worksheet("Students")
        # Column B = Student Name
        name_col_values = students_sheet.col_values(2)
        for row_idx, name in enumerate(name_col_values, start=1):
            if name and name.strip().lower() == student_name.strip().lower():
                existing_id = students_sheet.cell(row_idx, 1).value # Column A = Student_ID
                if existing_id:
                    return existing_id
        return base_id
    except Exception:
        return base_id

def flush_pending_logs():
    """Flush batched logs to sheets."""
    if not st.session_state.pending_logs:
        return
    try:
        sheet = get_sheets_client()
        if sheet:
            activity_sheet = sheet.worksheet("Activity_Log")
            activity_sheet.append_rows(st.session_state.pending_logs)
            st.session_state.pending_logs.clear()
    except Exception:
        pass  # Silent fail

def log_student_activity(student_id, student_name, question_type, strand, correct, time_seconds):
    """Log each question attempt (batched)."""
    try:
        timestamp = datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            student_id,
            student_name,
            question_type,
            strand,
            "Yes" if correct else "No",
            time_seconds,
        ]
        st.session_state.pending_logs.append(row)
        st.session_state.daily_usage["count"] += 1
        if len(st.session_state.pending_logs) >= 5:
            flush_pending_logs()
    except Exception:
        pass  # Silent fail

def update_student_summary(student_id, student_name):
    """Update overall student statistics (with flush)."""
    flush_pending_logs()  # Ensure logs are saved
    try:
        sheet = get_sheets_client()
        if sheet:
            students_sheet = sheet.worksheet("Students")
            try:
                cell = students_sheet.find(student_id)
                row_num = cell.row
                students_sheet.update_cell(row_num, 4, st.session_state.questions_answered)
                students_sheet.update_cell(row_num, 5, st.session_state.correct_answers)
                accuracy = (
                    round(
                        (st.session_state.correct_answers / st.session_state.questions_answered * 100),
                        1,
                    )
                    if st.session_state.questions_answered > 0
                    else 0
                )
                students_sheet.update_cell(row_num, 6, f"{accuracy}%")
                time_minutes = round((datetime.now(TT_TZ) - st.session_state.session_start).seconds / 60)
                current_time = int(students_sheet.cell(row_num, 7).value or 0)
                students_sheet.update_cell(row_num, 7, current_time + time_minutes)
                students_sheet.update_cell(
                    row_num, 8, datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M")
                )
            except Exception:
                students_sheet.append_row(
                    [
                        student_id,
                        student_name,
                        datetime.now(TT_TZ).strftime("%Y-%m-%d"),
                        st.session_state.questions_answered,
                        st.session_state.correct_answers,
                        f"{round((st.session_state.correct_answers / st.session_state.questions_answered * 100), 1) if st.session_state.questions_answered > 0 else 0}%",
                        round(
                            (datetime.now(TT_TZ) - st.session_state.session_start).seconds / 60
                        )
                        if st.session_state.session_start
                        else 0,
                        datetime.now(TT_TZ).strftime("%Y-%m-%d %H:%M"),
                    ]
                )
    except Exception:
        pass

# ============================================
# PROTECTION LAYERS (using cached client)
# ============================================
def check_global_limit():
    """Layer 3: Global daily cap"""
    GLOBAL_DAILY_LIMIT = int(st.secrets.get("global_daily_limit", 1000))
    try:
        sheet = get_sheets_client()
        if sheet:
            activity_sheet = sheet.worksheet("Activity_Log")
            today = get_tt_date().isoformat()
            all_records = activity_sheet.get_all_records()
            today_count = sum(
                1 for record in all_records if str(record.get("Timestamp", "")).startswith(today)
            )
            if today_count >= GLOBAL_DAILY_LIMIT:
                st.error("🚨 Daily Capacity Reached")
                st.info(
                    f"""
                The SEA Math Tutor has reached its daily capacity of {GLOBAL_DAILY_LIMIT} questions.
               
                **Your progress is saved!** Try again tomorrow (resets at midnight).
               
                Thank you for understanding! 🙏
                """
                )
                st.stop()
    except Exception:
        pass

def check_daily_limit():
    """Layer 2: Per-student daily limit"""
    DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
    today = get_tt_date().isoformat()
    if st.session_state.daily_usage["date"] != today:
        st.session_state.daily_usage = {"date": today, "count": 0}
    if st.session_state.daily_usage["count"] >= DAILY_LIMIT:
        st.warning("🎯 Daily Practice Goal Reached!")
        st.success(
            f"""
        Awesome work! You've completed {DAILY_LIMIT} questions today! 🎉
       
        **Your progress is saved!**
       
        💡 **Why rest?**
        - Your brain needs time to process
        - Come back tomorrow fresh!
       
        Great job, champion! 💪
        """
        )
        if st.button("🚪 Exit for Today"):
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
            for key in list(st.session_state.keys()):
                if not key.startswith("_"):
                    del st.session_state[key]
            st.rerun()
        st.stop()

# ============================================
# CHAT SESSION HELPER (90% TOKEN SAVINGS!)
# ============================================
def get_or_create_chat():
    if "gemini_chat" not in st.session_state:
        model = get_gemini_model()
        chat = model.start_chat(history=[
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood! I will follow every rule perfectly."]}
        ])
        st.session_state.gemini_chat = chat
    return st.session_state.gemini_chat

# ============================================
# DASHBOARD SCREEN
# ============================================
def show_dashboard():
    """Main dashboard with topic selection"""
    st.markdown(
        """
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #667eea; font-size: 48px; margin-bottom: 10px;'>
            🎓 SEA Math Super-Tutor
        </h1>
        <p style='color: #444; font-size: 20px;'>
            Your Friendly AI Math Coach for SEA Success!
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    # LOGIN SECTION
    if not st.session_state.student_name:
        st.markdown(
            """
        <div style='background: linear-gradient(135deg, #f97316 0%, #ec4899 100%);
                    padding: 30px; border-radius: 18px; margin: 20px 0; box-shadow: 0 8px 24px rgba(0,0,0,0.12);'>
            <h2 style='color: white; margin-bottom: 10px;'>👋 Welcome! Let's Get Started</h2>
            <p style='color: #fef2f2; margin: 0; font-size: 16px;'>
                Fill in your details below to begin your SEA Math training.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
        with col1:
            first_name = st.text_input("First Name", key="input_first")
        with col2:
            last_name = st.text_input("Last Name", key="input_last")
        with col3:
            class_code = st.text_input("Class Code", type="password", key="input_code")
        with col4:
            st.write("")
            st.write("")
            if st.button("✅ Enter"):
                if first_name and last_name and class_code:
                    valid_codes = st.secrets.get("class_codes", "MATH2025,SEA2025").split(",")
                    if class_code.upper() in [c.strip().upper() for c in valid_codes]:
                        full_name = f"{first_name} {last_name}"
                        st.session_state.student_name = full_name
                        st.session_state.first_name = first_name
                        st.session_state.student_id = get_or_create_student_id(full_name)
                        st.session_state.session_start = datetime.now(TT_TZ)
                        st.rerun()
                    else:
                        st.error("❌ Invalid class code. Please check with your teacher.")
                else:
                    st.warning("Please fill in all fields!")
        st.info("📧 **Teachers:** Contact your school to get a class code")
        return
    # LOGGED IN - Show dashboard
    check_global_limit()
    check_daily_limit()
    # Welcome banner
    st.markdown(
        f"""
    <div style='background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
                padding: 20px 30px; border-radius: 18px; margin: 20px 0;
                box-shadow: 0 10px 30px rgba(15,23,42,0.3);'>
        <h2 style='color: white; margin: 0;'>Welcome back, {st.session_state.first_name}! 🎉</h2>
        <p style='color: #e0f2fe; margin: 5px 0 0 0; font-size: 16px;'>
            Ready to become a math champion today?
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("📊 View Progress"):
            show_progress_modal()
    st.write("")
    # Topics section
    st.markdown(
        "<h3 style='text-align: center; color: #111827;'>📚 Choose Your Topic</h3>",
        unsafe_allow_html=True,
    )
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🔢 Number\n\nFractions, Decimals, Percentages, Patterns\n\n**34 marks on SEA**",
            key="btn_number",
        ):
            start_practice("Number")
        if st.button(
            "📐 Geometry\n\nShapes, Symmetry, Angles, Properties\n\n**11 marks on SEA**",
            key="btn_geometry",
        ):
            start_practice("Geometry")
    with col2:
        if st.button(
            "📏 Measurement\n\nLength, Area, Perimeter, Volume, Time\n\n**18 marks on SEA**",
            key="btn_measurement",
        ):
            start_practice("Measurement")
        if st.button(
            "📊 Statistics\n\nGraphs, Mean, Mode, Data Analysis\n\n**12 marks on SEA**",
            key="btn_statistics",
        ):
            start_practice("Statistics")
    st.write("")
    st.markdown(
        "<h3 style='text-align: center; color: #111827;'>🎯 Or Choose Practice Mode</h3>",
        unsafe_allow_html=True,
    )
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🎲 Mixed Practice\n\nQuestions from all topics - like the real exam!",
            key="btn_mixed",
        ):
            start_practice("Mixed")
    with col2:
        if st.button(
            "📝 Full SEA Practice Test\n\nComplete 40-question timed exam",
            key="btn_fulltest",
        ):
            start_practice("Full Test")
    st.write("")
    st.write("")
    # Exit button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 Exit"):
            if st.session_state.questions_answered > 0:
                update_student_summary(st.session_state.student_id, st.session_state.student_name)
            for key in list(st.session_state.keys()):
                if not key.startswith("_"):
                    del st.session_state[key]
            st.rerun()

def start_practice(topic):
    """Start practice mode for selected topic"""
    st.session_state.current_topic = topic
    st.session_state.screen = "practice"
    st.session_state.conversation_history = []
    # Track when the current question was asked
    st.session_state.question_start_time = datetime.now(TT_TZ)
    st.rerun()

def show_progress_modal():
    """Show progress in a modal-like display"""
    with st.expander("📊 Your Progress", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Questions Today", st.session_state.questions_answered)
        with col2:
            accuracy = (
                round(
                    (st.session_state.correct_answers / st.session_state.questions_answered * 100)
                )
                if st.session_state.questions_answered > 0
                else 0
            )
            st.metric("Accuracy", f"{accuracy}%")
        with col3:
            DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
            remaining = DAILY_LIMIT - st.session_state.daily_usage["count"]
            st.metric("Questions Left", remaining)
        DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
        progress_ratio = min(st.session_state.daily_usage["count"] / DAILY_LIMIT, 1.0)
        st.progress(progress_ratio)

# ============================================
# PRACTICE SCREEN (with chat session & better detection)
# ============================================
def show_practice_screen():
    """Immersive practice mode"""
    check_global_limit()
    check_daily_limit()
    # Header with exit
    col1, col2 = st.columns([5, 1])
    with col1:
        topic_icons = {
            "Number": "🔢",
            "Measurement": "📏",
            "Geometry": "📐",
            "Statistics": "📊",
            "Mixed": "🎲",
            "Full Test": "📝",
        }
        icon = topic_icons.get(st.session_state.current_topic, "📚")
        st.title(f"{icon} {st.session_state.current_topic} Practice")
    with col2:
        st.write("")
        if st.button("🚪 Exit"):
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
            st.session_state.screen = "dashboard"
            st.session_state.current_topic = None
            st.rerun()
    # Stats bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions", st.session_state.questions_answered)
    with col2:
        st.metric("Correct", st.session_state.correct_answers)
    with col3:
        accuracy = (
            round(
                (st.session_state.correct_answers / st.session_state.questions_answered * 100)
            )
            if st.session_state.questions_answered > 0
            else 0
        )
        st.metric("Accuracy", f"{accuracy}%")
    with col4:
        if st.session_state.session_start:
            elapsed = datetime.now(TT_TZ) - st.session_state.session_start
            mins = int(elapsed.total_seconds() / 60)
            st.metric("Time", f"{mins} min")
    st.write("---")
    # Chat interface
    for message in st.session_state.conversation_history:
        with st.chat_message(
            message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"
        ):
            st.write(message["content"])
    # User input
    if prompt := st.chat_input("Type your answer or 'Next' for a question..."):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        model = get_gemini_model()
        if model:
            chat = get_or_create_chat()
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    # Build context without full history loop (chat handles it)
                    context = f"Student: {st.session_state.first_name}\nTopic: {st.session_state.current_topic}\nQuestions so far: {st.session_state.questions_answered}\n\n{prompt}"
                    try:
                        response = chat.send_message(context)
                        response_text = response.text
                    except Exception:
                        st.error("Sorry, I'm having trouble thinking right now. Please try again.")
                        return
                    st.write(response_text)
                    st.session_state.conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )
                    # IMPROVED: Simpler, more reliable correctness detection
                    first_line = response_text.splitlines()[0].strip().lower()
                    correct_markers = [
                        "✅", "✓", "correct!", "yes!", "excellent!", "great job!", "well done!",
                        "perfect!", "right!", "exactly!", "spot on!", "you got it"
                    ]
                    incorrect_markers = [
                        "❌", "✗", "not quite", "incorrect", "that's not right", "try again",
                        "not correct", "wrong", "almost"
                    ]
                    has_correct = any(marker in first_line for marker in correct_markers)
                    has_incorrect = any(marker in first_line for marker in incorrect_markers)
                    is_feedback = has_correct or has_incorrect
                    if is_feedback:
                        st.session_state.questions_answered += 1
                        is_correct = has_correct
                        if is_correct:
                            st.session_state.correct_answers += 1
                        # Time taken
                        question_start = st.session_state.get("question_start_time", datetime.now(TT_TZ))
                        elapsed = datetime.now(TT_TZ) - question_start
                        time_seconds = int(elapsed.total_seconds())
                        log_student_activity(
                            st.session_state.student_id,
                            st.session_state.student_name,
                            "Question",
                            st.session_state.current_topic,
                            is_correct,
                            time_seconds,
                        )
                        # Reset for next question
                        st.session_state.question_start_time = datetime.now(TT_TZ)
    # Initial prompt
    if len(st.session_state.conversation_history) == 0:
        st.info(
            f"👋 Hi {st.session_state.first_name}! "
            f"Type **'Start'** or **'Give me a question'** to begin!"
        )

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
