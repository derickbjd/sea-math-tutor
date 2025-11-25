import streamlit as st
import google.generativeai as genai
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials  # UPDATED AUTH IMPORT
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
    /* ===== Global page styling ===== */
    .stApp {
        background-color: #f5f7fb;  /* soft light grey/blue */
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
        color: #111827 !important;   /* dark grey text */
    }

    /* User vs assistant bubbles for a bit of fun */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #e0f2fe !important;  /* light blue */
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
        background: linear-gradient(135deg, #4f46e5, #6366f1);  /* indigo gradient */
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

    /* Active / focused state – CRITICAL: keep text visible */
    .stButton > button:active,
    .stButton > button:focus {
        outline: none !important;
        border: none !important;
        background: linear-gradient(135deg, #4338ca, #4f46e5);  /* slightly darker */
        color: #ffffff !important;  /* stay white text */
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

    /* You can optionally give different colours to different buttons
       later by targeting their specific keys with data-testid if needed. */
       def load_css():
    st.markdown("""
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Custom button styling */
    .stButton button {
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    /* Topic cards */
    div[data-testid="column"] > div > div > button {
        height: 120px;
        white-space: pre-wrap;
    }

    /* Hide Streamlit's "user" / "assistant" chat labels */
    [data-testid="stChatMessage"] > div:first-child {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    </style>
    """, unsafe_allow_html=True)

load_css()

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if 'screen' not in st.session_state:
    st.session_state.screen = 'dashboard'
if 'student_name' not in st.session_state:
    st.session_state.student_name = None
if 'student_id' not in st.session_state:
    st.session_state.student_id = None
if 'first_name' not in st.session_state:
    st.session_state.first_name = None
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = None
if 'questions_answered' not in st.session_state:
    st.session_state.questions_answered = 0
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = 0
if 'session_start' not in st.session_state:
    st.session_state.session_start = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'daily_usage' not in st.session_state:
    today = date.today().isoformat()
    st.session_state.daily_usage = {'date': today, 'count': 0}
if 'badge_progress' not in st.session_state:
    st.session_state.badge_progress = {
        'number': 0,
        'measurement': 0,
        'geometry': 0,
        'statistics': 0
    }

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================

def connect_to_sheets():
    """Connect to Google Sheets for data logging using service account from Streamlit secrets"""
    try:
        # st.secrets["google_sheets"] must contain your service account JSON as a dict
        creds_info = st.secrets["google_sheets"]

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)

        # This must match the exact name of your spreadsheet in Google Drive
        sheet = client.open("SEA_Math_Tutor_Data")
        return sheet
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None


def get_or_create_student_id(student_name: str) -> str:
    """
    Return an existing Student_ID for this student_name if it exists in the
    'Students' worksheet. Otherwise, create a deterministic new one based
    only on the name so it stays stable across sessions.
    """
    base_id = f"STU{abs(hash(student_name))}".replace("-", "")[:10]

    try:
        sheet = connect_to_sheets()
        if not sheet:
            # If we cannot reach Sheets, fall back to deterministic ID
            return base_id

        students_sheet = sheet.worksheet("Students")

        # Get all names in column 2 (B) where we store Student Name
        name_col_values = students_sheet.col_values(2)  # 1-based index

        # Search for a case-insensitive match
        for row_idx, name in enumerate(name_col_values, start=1):
            if name and name.strip().lower() == student_name.strip().lower():
                existing_id = students_sheet.cell(row_idx, 1).value  # Column A = Student_ID
                if existing_id:
                    return existing_id

        # No existing match, use deterministic new ID
        return base_id

    except Exception:
        # On any error, still fall back to deterministic ID based on name
        return base_id


def log_student_activity(student_id, student_name, question_type, strand, correct, time_seconds):
    """Log each question attempt"""
    try:
        sheet = connect_to_sheets()
        if sheet:
            activity_sheet = sheet.worksheet("Activity_Log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            activity_sheet.append_row([
                timestamp, student_id, student_name,
                question_type, strand,
                "Yes" if correct else "No",
                time_seconds
            ])
            # Increment usage
            if 'daily_usage' in st.session_state:
                st.session_state.daily_usage['count'] += 1
    except Exception:
        pass  # Silent fail


def update_student_summary(student_id, student_name):
    """Update overall student statistics"""
    try:
        sheet = connect_to_sheets()
        if sheet:
            students_sheet = sheet.worksheet("Students")
            try:
                cell = students_sheet.find(student_id)
                row_num = cell.row
                students_sheet.update_cell(row_num, 4, st.session_state.questions_answered)
                students_sheet.update_cell(row_num, 5, st.session_state.correct_answers)
                accuracy = round(
                    (st.session_state.correct_answers / st.session_state.questions_answered * 100),
                    1
                ) if st.session_state.questions_answered > 0 else 0
                students_sheet.update_cell(row_num, 6, f"{accuracy}%")
                time_minutes = round(
                    (datetime.now() - st.session_state.session_start).seconds / 60
                )
                current_time = int(students_sheet.cell(row_num, 7).value or 0)
                students_sheet.update_cell(row_num, 7, current_time + time_minutes)
                students_sheet.update_cell(row_num, 8, datetime.now().strftime("%Y-%m-%d %H:%M"))
            except Exception:
                # If this Student_ID doesn't exist yet, append new row
                students_sheet.append_row([
                    student_id, student_name,
                    datetime.now().strftime("%Y-%m-%d"),
                    st.session_state.questions_answered,
                    st.session_state.correct_answers,
                    f"{round((st.session_state.correct_answers / st.session_state.questions_answered * 100), 1) if st.session_state.questions_answered > 0 else 0}%",
                    round((datetime.now() - st.session_state.session_start).seconds / 60) if st.session_state.session_start else 0,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ])
    except Exception:
        pass

# ============================================
# PROTECTION LAYERS
# ============================================

def check_global_limit():
    """Layer 3: Global daily cap"""
    GLOBAL_DAILY_LIMIT = int(st.secrets.get("global_daily_limit", 1000))

    try:
        sheet = connect_to_sheets()
        if sheet:
            activity_sheet = sheet.worksheet("Activity_Log")
            today = date.today().isoformat()
            all_records = activity_sheet.get_all_records()
            today_count = sum(
                1 for record in all_records
                if str(record.get('Timestamp', '')).startswith(today)
            )

            if today_count >= GLOBAL_DAILY_LIMIT:
                st.error("🚨 Daily Capacity Reached")
                st.info(f"""
                The SEA Math Tutor has reached its daily capacity of {GLOBAL_DAILY_LIMIT} questions.
                
                **Your progress is saved!** Try again tomorrow (resets at midnight).
                
                Thank you for understanding! 🙏
                """)
                st.stop()
    except Exception:
        pass


def check_daily_limit():
    """Layer 2: Per-student daily limit"""
    DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
    today = date.today().isoformat()

    if st.session_state.daily_usage['date'] != today:
        st.session_state.daily_usage = {'date': today, 'count': 0}

    if st.session_state.daily_usage['count'] >= DAILY_LIMIT:
        st.warning("🎯 Daily Practice Goal Reached!")
        st.success(f"""
        Awesome work! You've completed {DAILY_LIMIT} questions today! 🎉
        
        **Your progress is saved!**
        
        💡 **Why rest?**
        - Your brain needs time to process
        - Come back tomorrow fresh!
        
        Great job, champion! 💪
        """)

        if st.button("🚪 Exit for Today", type="primary"):
            update_student_summary(st.session_state.student_id, st.session_state.student_name)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.stop()

# ============================================
# AI CONFIGURATION
# ============================================

def configure_gemini():
    """Configure Google Gemini AI"""
    try:
        genai.configure(api_key=st.secrets["google_api_key"])
        # Use one of your available models (from the list you printed)
        return genai.GenerativeModel("models/gemini-flash-latest")
    except Exception as e:
        st.error(f"Could not configure AI: {e}")
        return None


SYSTEM_PROMPT = """You are the SEA Math Super-Tutor for Trinidad & Tobago students preparing for their Secondary Entrance Assessment.

YOUR ROLE:
- Create SEA-standard questions based on official framework
- Test: Number (34 marks), Measurement (18 marks), Geometry (11 marks), Statistics (12 marks)
- Use 11-year-old friendly language
- Give ONE question at a time
- After they answer, tell if correct and explain
- Teach shortcuts and hacks

CRITICAL - ANSWER FEEDBACK FORMAT:
When student answers, you MUST start your response with one of these:
- If CORRECT: Start with "✅ Correct!" or "🎉 Yes!" or "✓ Right!" or "Excellent!"
- If WRONG: Start with "❌ Not quite" or "That's not correct" or "Try again"

This is VERY IMPORTANT for tracking their progress!

QUESTION TYPES:
NUMBER: Whole numbers, fractions, decimals, percentages, patterns
MEASUREMENT: Length, area, perimeter, volume, time
GEOMETRY: Shapes, symmetry, angles
STATISTICS: Graphs, mean, mode

TEACHING STYLE:
- Simple, clear language
- Use Trinidad examples when possible
- Celebrate wins: "Yes! 🎉"
- When wrong: explain kindly, show method, give hack
- Use analogies

HACKS TO TEACH:
- Divide by 25: Multiply by 4, divide by 100
- Multiply by 5: Multiply by 10, divide by 2
- Find 10%: Move decimal left
- Perimeter rectangle: (L + W) × 2

FORMAT:
1. If they say "start" or "next": Give a question, then say "This is a [strand] question"
2. If they give an answer: 
   - FIRST LINE: ✅ Correct! OR ❌ Not quite
   - Then explain why
   - Then teach a hack
   - Then ask if they want another
3. Keep responses short (2-3 paragraphs)
4. Use emojis!

EXAMPLE GOOD RESPONSES:
"✅ Correct! You got it, Marcus! The answer is 46m. Here's why: The perimeter..."
"❌ Not quite, but good try! The answer is actually 46m, not 23m. Here's what happened..."

You're helping them become champions! 🏆"""

# ============================================
# DASHBOARD SCREEN
# ============================================

def show_dashboard():
    """Main dashboard with topic selection"""

    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #667eea; font-size: 48px; margin-bottom: 10px;'>
            🎓 SEA Math Super-Tutor
        </h1>
        <p style='color: #444; font-size: 20px;'>
            Your Friendly AI Math Coach for SEA Success!
        </p>
    </div>
    """, unsafe_allow_html=True)

    # LOGIN SECTION
    if not st.session_state.student_name:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f97316 0%, #ec4899 100%); 
                    padding: 30px; border-radius: 18px; margin: 20px 0; box-shadow: 0 8px 24px rgba(0,0,0,0.12);'>
            <h2 style='color: white; margin-bottom: 10px;'>👋 Welcome! Let's Get Started</h2>
            <p style='color: #fef2f2; margin: 0; font-size: 16px;'>
                Fill in your details below to begin your SEA Math training.
            </p>
        </div>
        """, unsafe_allow_html=True)

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
            if st.button("✅ Enter", type="primary"):
                if first_name and last_name and class_code:
                    # Layer 1: Check class code
                    valid_codes = st.secrets.get("class_codes", "MATH2025,SEA2025").split(",")
                    if class_code.upper() in [c.strip().upper() for c in valid_codes]:
                        full_name = f"{first_name} {last_name}"
                        st.session_state.student_name = full_name
                        st.session_state.first_name = first_name
                        # 🔑 Stable Student ID across sessions
                        st.session_state.student_id = get_or_create_student_id(full_name)
                        st.session_state.session_start = datetime.now()
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
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%); 
                padding: 20px 30px; border-radius: 18px; margin: 20px 0;
                box-shadow: 0 10px 30px rgba(15,23,42,0.3);'>
        <h2 style='color: white; margin: 0;'>Welcome back, {st.session_state.first_name}! 🎉</h2>
        <p style='color: #e0f2fe; margin: 5px 0 0 0; font-size: 16px;'>
            Ready to become a math champion today?
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("📊 View Progress"):
            show_progress_modal()

    st.write("")

    # Topics section
    st.markdown("<h3 style='text-align: center; color: #111827;'>📚 Choose Your Topic</h3>", unsafe_allow_html=True)
    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔢 Number\n\nFractions, Decimals, Percentages, Patterns\n\n**34 marks on SEA**",
                     key="btn_number"):
            start_practice("Number")

        if st.button("📐 Geometry\n\nShapes, Symmetry, Angles, Properties\n\n**11 marks on SEA**",
                     key="btn_geometry"):
            start_practice("Geometry")

    with col2:
        if st.button("📏 Measurement\n\nLength, Area, Perimeter, Volume, Time\n\n**18 marks on SEA**",
                     key="btn_measurement"):
            start_practice("Measurement")

        if st.button("📊 Statistics\n\nGraphs, Mean, Mode, Data Analysis\n\n**12 marks on SEA**",
                     key="btn_statistics"):
            start_practice("Statistics")

    st.write("")
    st.markdown("<h3 style='text-align: center; color: #111827;'>🎯 Or Choose Practice Mode</h3>", unsafe_allow_html=True)
    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🎲 Mixed Practice\n\nQuestions from all topics - like the real exam!",
                     key="btn_mixed"):
            start_practice("Mixed")

    with col2:
        if st.button("📝 Full SEA Practice Test\n\nComplete 40-question timed exam",
                     key="btn_fulltest"):
            start_practice("Full Test")

    st.write("")
    st.write("")

    # Exit button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 Exit", type="secondary"):
            if st.session_state.questions_answered > 0:
                update_student_summary(st.session_state.student_id, st.session_state.student_name)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def start_practice(topic):
    """Start practice mode for selected topic"""
    st.session_state.current_topic = topic
    st.session_state.screen = 'practice'
    st.session_state.conversation_history = []
    st.rerun()


def show_progress_modal():
    """Show progress in a modal-like display"""
    with st.expander("📊 Your Progress", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Questions Today", st.session_state.questions_answered)
        with col2:
            accuracy = round(
                (st.session_state.correct_answers / st.session_state.questions_answered * 100)
            ) if st.session_state.questions_answered > 0 else 0
            st.metric("Accuracy", f"{accuracy}%")
        with col3:
            DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
            remaining = DAILY_LIMIT - st.session_state.daily_usage['count']
            st.metric("Questions Left", remaining)

        DAILY_LIMIT = int(st.secrets.get("daily_limit_per_student", 50))
        progress_ratio = min(st.session_state.daily_usage['count'] / DAILY_LIMIT, 1.0)
        st.progress(progress_ratio)

# ============================================
# PRACTICE SCREEN
# ============================================

def show_practice_screen():
    """Immersive practice mode"""

    check_global_limit()
    check_daily_limit()

    # Header with exit
    col1, col2 = st.columns([5, 1])

    with col1:
        topic_icons = {
            'Number': '🔢', 'Measurement': '📏',
            'Geometry': '📐', 'Statistics': '📊',
            'Mixed': '🎲', 'Full Test': '📝'
        }
        icon = topic_icons.get(st.session_state.current_topic, '📚')
        st.title(f"{icon} {st.session_state.current_topic} Practice")

    with col2:
        st.write("")
        if st.button("🚪 Exit", type="secondary"):
            if st.session_state.questions_answered > 0:
                update_student_summary(st.session_state.student_id, st.session_state.student_name)
            st.session_state.screen = 'dashboard'
            st.session_state.current_topic = None
            st.rerun()

    # Stats bar
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Questions", st.session_state.questions_answered)
    with col2:
        st.metric("Correct", st.session_state.correct_answers)
    with col3:
        accuracy = round(
            (st.session_state.correct_answers / st.session_state.questions_answered * 100)
        ) if st.session_state.questions_answered > 0 else 0
        st.metric("Accuracy", f"{accuracy}%")
    with col4:
        if st.session_state.session_start:
            elapsed = datetime.now() - st.session_state.session_start
            mins = int(elapsed.total_seconds() / 60)
            st.metric("Time", f"{mins} min")

    st.write("---")

    # Chat interface
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
            st.write(message["content"])

    # User input
    if prompt := st.chat_input("Type your answer or 'Next' for a question..."):
        st.session_state.conversation_history.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        # Get AI response
        model = configure_gemini()
        if model:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    full_prompt = SYSTEM_PROMPT + "\n\n"
                    full_prompt += f"Student: {st.session_state.first_name}\n"
                    full_prompt += f"Topic: {st.session_state.current_topic}\n"
                    full_prompt += f"Questions so far: {st.session_state.questions_answered}\n\n"

                    for msg in st.session_state.conversation_history[-10:]:
                        full_prompt += f"{msg['role']}: {msg['content']}\n"

                    response = model.generate_content(full_prompt)
                    response_text = response.text

                    st.write(response_text)

                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": response_text
                    })

                    # Parse AI response to detect correct/incorrect
                    response_lower = response_text.lower()

                    # Check if this is feedback on an answer (not just a question)
                    is_question = (
                        'what is' in response_lower
                        or 'calculate' in response_lower
                        or 'find' in response_lower
                        or 'how many' in response_lower
                    )

                    # Look for explicit correct/incorrect markers
                    correct_markers = [
                        '✅', '✓', 'correct!', 'yes!', 'excellent!', 'great job!',
                        'well done!', 'perfect!', 'right!', 'exactly!', 'spot on!',
                        'you got it'
                    ]
                    incorrect_markers = [
                        '❌', '✗', 'not quite', 'incorrect', "that's not right",
                        'try again', 'not correct', 'wrong', 'almost'
                    ]

                    has_correct_marker = any(marker in response_lower for marker in correct_markers)
                    has_incorrect_marker = any(marker in response_lower for marker in incorrect_markers)

                    # This is feedback if it has markers and isn't asking a question
                    is_feedback = (has_correct_marker or has_incorrect_marker) and not is_question

                    if is_feedback:
                        # Update stats
                        st.session_state.questions_answered += 1

                        if has_correct_marker:
                            st.session_state.correct_answers += 1
                            is_correct = True
                        else:
                            is_correct = False

                        # Log activity
                        try:
                            log_student_activity(
                                st.session_state.student_id,
                                st.session_state.student_name,
                                "Question",
                                st.session_state.current_topic,
                                is_correct,
                                30
                            )
                        except Exception:
                            pass

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
    if st.session_state.screen == 'practice':
        show_practice_screen()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
