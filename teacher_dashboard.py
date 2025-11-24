import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ============================================
# CONFIGURATION
# ============================================

st.set_page_config(
    page_title="Teacher Dashboard - SEA Math Tutor",
    page_icon="👨‍🏫",
    layout="wide"
)

# ============================================
# AUTHENTICATION
# ============================================

def check_password():
    """Simple password protection for teacher dashboard"""
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("👨‍🏫 Teacher Dashboard Login")
        st.write("### SEA Math Super-Tutor")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("Enter Teacher Password:", type="password")
            
            if st.button("Login", type="primary", use_container_width=True):
                # You can change this password in secrets
                if password == st.secrets.get("teacher_password", "SEATeacher2025"):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password!")
        
        st.stop()

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================

@st.cache_resource
def connect_to_sheets():
    """Connect to Google Sheets"""
    try:
        creds_dict = st.secrets["google_sheets"]
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("SEA_Math_Tutor_Data")
        return sheet
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None

@st.cache_data(ttl=60)  # Cache for 1 minute
def load_student_data():
    """Load all student summary data"""
    try:
        sheet = connect_to_sheets()
        if sheet:
            students_sheet = sheet.worksheet("Students")
            data = students_sheet.get_all_records()
            df = pd.DataFrame(data)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading student data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_activity_log():
    """Load activity log data"""
    try:
        sheet = connect_to_sheets()
        if sheet:
            activity_sheet = sheet.worksheet("Activity_Log")
            data = activity_sheet.get_all_records()
            df = pd.DataFrame(data)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading activity log: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_badges():
    """Load badge data"""
    try:
        sheet = connect_to_sheets()
        if sheet:
            badges_sheet = sheet.worksheet("Badges")
            data = badges_sheet.get_all_records()
            df = pd.DataFrame(data)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading badges: {e}")
        return pd.DataFrame()

# ============================================
# DASHBOARD FUNCTIONS
# ============================================

def class_overview():
    """Display class-wide statistics"""
    st.header("📊 Class Overview")
    
    students_df = load_student_data()
    
    if students_df.empty:
        st.warning("No student data yet. Students will appear here once they start practicing!")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Students", len(students_df))
    
    with col2:
        active_today = len(students_df[pd.to_datetime(students_df['Last_Active']).dt.date == datetime.now().date()])
        st.metric("Active Today", active_today)
    
    with col3:
        total_questions = students_df['Total_Questions'].sum()
        st.metric("Total Questions", f"{total_questions:,}")
    
    with col4:
        # Calculate class average accuracy
        students_df['Accuracy_Num'] = students_df['Accuracy'].str.rstrip('%').astype(float)
        avg_accuracy = students_df['Accuracy_Num'].mean()
        st.metric("Class Avg Accuracy", f"{avg_accuracy:.1f}%")
    
    st.write("---")
    
    # Student table
    st.subheader("👥 All Students")
    
    # Prepare display dataframe
    display_df = students_df[['Name', 'Total_Questions', 'Correct', 'Accuracy', 'Time_Minutes', 'Last_Active']].copy()
    display_df.columns = ['Student Name', 'Questions', 'Correct', 'Accuracy', 'Time (min)', 'Last Active']
    
    # Sort by questions answered
    display_df = display_df.sort_values('Questions', ascending=False)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Class Report (CSV)",
        data=csv,
        file_name=f"class_report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def student_detail(student_name):
    """Display detailed view of individual student"""
    st.header(f"📊 {student_name} - Progress Report")
    
    students_df = load_student_data()
    activity_df = load_activity_log()
    badges_df = load_badges()
    
    # Get student data
    student_row = students_df[students_df['Name'] == student_name].iloc[0]
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Questions", student_row['Total_Questions'])
    
    with col2:
        st.metric("Correct Answers", f"{student_row['Correct']} ({student_row['Accuracy']})")
    
    with col3:
        st.metric("Time Spent", f"{student_row['Time_Minutes']} min")
    
    with col4:
        student_badges = badges_df[badges_df['Student_Name'] == student_name]
        st.metric("Badges Earned", len(student_badges))
    
    st.write("---")
    
    # Performance by strand
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance by Strand")
        
        # Get student's activity by strand
        student_activity = activity_df[activity_df['Student_Name'] == student_name]
        
        if not student_activity.empty:
            strand_performance = student_activity.groupby('Strand').agg({
                'Correct': lambda x: (x == 'Yes').sum(),
                'Student_ID': 'count'
            }).reset_index()
            strand_performance.columns = ['Strand', 'Correct', 'Total']
            strand_performance['Accuracy'] = (strand_performance['Correct'] / strand_performance['Total'] * 100).round(1)
            
            # Create bar chart
            fig = px.bar(strand_performance, x='Strand', y='Accuracy', 
                        title='Accuracy by Strand (%)',
                        color='Accuracy',
                        color_continuous_scale='RdYlGn',
                        range_color=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
            
            # Display table
            st.dataframe(strand_performance, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🏆 Badges Earned")
        
        if not student_badges.empty:
            for _, badge in student_badges.iterrows():
                st.success(f"{badge['Badge_Name']} - Earned on {badge['Date_Earned']}")
        else:
            st.info("No badges earned yet. Keep practicing!")
    
    st.write("---")
    
    # Recent activity
    st.subheader("📅 Recent Activity")
    
    if not student_activity.empty:
        # Show last 20 questions
        recent = student_activity.tail(20).sort_values('Timestamp', ascending=False)
        display_recent = recent[['Timestamp', 'Question_Type', 'Strand', 'Correct', 'Time_Seconds']].copy()
        display_recent.columns = ['Time', 'Question Type', 'Strand', 'Result', 'Time (sec)']
        display_recent['Result'] = display_recent['Result'].apply(lambda x: '✅' if x == 'Yes' else '❌')
        
        st.dataframe(display_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded yet.")
    
    # Common mistakes
    st.write("---")
    st.subheader("⚠️ Areas Needing Attention")
    
    if not student_activity.empty:
        # Find strands with low accuracy
        weak_strands = strand_performance[strand_performance['Accuracy'] < 70]
        
        if not weak_strands.empty:
            for _, strand in weak_strands.iterrows():
                st.warning(f"**{strand['Strand']}**: {strand['Accuracy']:.1f}% accuracy - needs more practice")
        else:
            st.success("Great performance across all strands! 🎉")
    
    # Strengths
    st.subheader("✅ Strengths")
    
    if not student_activity.empty:
        strong_strands = strand_performance[strand_performance['Accuracy'] >= 80]
        
        if not strong_strands.empty:
            for _, strand in strong_strands.iterrows():
                st.success(f"**{strand['Strand']}**: {strand['Accuracy']:.1f}% accuracy - Excellent! 💪")

def analytics_page():
    """Advanced analytics and insights"""
    st.header("📊 Analytics & Insights")
    
    students_df = load_student_data()
    activity_df = load_activity_log()
    
    if students_df.empty or activity_df.empty:
        st.warning("Not enough data yet for analytics.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Most Practiced Topics")
        
        # Count questions by strand
        strand_counts = activity_df['Strand'].value_counts()
        fig = px.pie(values=strand_counts.values, names=strand_counts.index, 
                     title='Questions by Strand')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Class Performance Trends")
        
        # Accuracy by strand
        strand_accuracy = activity_df.groupby('Strand').agg({
            'Correct': lambda x: (x == 'Yes').sum() / len(x) * 100
        }).reset_index()
        strand_accuracy.columns = ['Strand', 'Accuracy']
        
        fig = px.bar(strand_accuracy, x='Strand', y='Accuracy',
                    title='Average Accuracy by Strand (%)',
                    color='Accuracy',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    
    st.write("---")
    
    # Time distribution
    st.subheader("⏰ Usage Patterns")
    
    # Parse timestamps
    activity_df['Datetime'] = pd.to_datetime(activity_df['Timestamp'])
    activity_df['Hour'] = activity_df['Datetime'].dt.hour
    activity_df['Date'] = activity_df['Datetime'].dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Questions by hour
        hourly = activity_df['Hour'].value_counts().sort_index()
        fig = px.bar(x=hourly.index, y=hourly.values,
                    labels={'x': 'Hour of Day', 'y': 'Number of Questions'},
                    title='Activity by Hour of Day')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Questions by date
        daily = activity_df['Date'].value_counts().sort_index()
        fig = px.line(x=daily.index, y=daily.values,
                     labels={'x': 'Date', 'y': 'Number of Questions'},
                     title='Activity Over Time')
        st.plotly_chart(fig, use_container_width=True)
    
    st.write("---")
    
    # Top performers
    st.subheader("🏆 Top Performers")
    
    students_df['Accuracy_Num'] = students_df['Accuracy'].str.rstrip('%').astype(float)
    top_students = students_df.nlargest(5, 'Accuracy_Num')[['Name', 'Total_Questions', 'Accuracy']]
    
    st.dataframe(top_students, use_container_width=True, hide_index=True)

# ============================================
# MAIN DASHBOARD
# ============================================

def main():
    """Main dashboard application"""
    
    # Check authentication
    check_password()
    
    # Title
    st.title("👨‍🏫 SEA Math Tutor - Teacher Dashboard")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio("Go to:", ["Class Overview", "Student Details", "Analytics", "Usage Monitoring"])
        
        st.write("---")
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.write("---")
        
        # Logout
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()
    
    # Display selected page
    if page == "Class Overview":
        class_overview()
    
    elif page == "Student Details":
        students_df = load_student_data()
        
        if students_df.empty:
            st.warning("No students yet!")
        else:
            student_name = st.selectbox("Select Student:", students_df['Name'].tolist())
            st.write("---")
            student_detail(student_name)
    
    elif page == "Analytics":
        analytics_page()
    
    elif page == "Usage Monitoring":
        usage_monitoring()

def usage_monitoring():
    """Monitor system usage and costs"""
    
    st.header("📊 System Usage & Limits")
    
    activity_df = load_activity_log()
    
    if not activity_df.empty:
        # Parse dates
        activity_df['Date'] = pd.to_datetime(activity_df['Timestamp']).dt.date
        today = date.today()
        
        # Today's usage
        today_questions = len(activity_df[activity_df['Date'] == today])
        
        # This week's usage
        week_start = today - timedelta(days=today.weekday())
        this_week = len(activity_df[activity_df['Date'] >= week_start])
        
        # This month's usage
        this_month = len(activity_df[activity_df['Date'].apply(
            lambda x: x.year == today.year and x.month == today.month
        )])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            limit = 1000  # Your global daily limit
            percentage = (today_questions / limit) * 100
            st.metric(
                "Today's Usage",
                f"{today_questions}/{limit}",
                f"{percentage:.1f}%"
            )
            st.progress(min(percentage / 100, 1.0))
        
        with col2:
            weekly_limit = limit * 7
            st.metric(
                "This Week",
                f"{this_week}/{weekly_limit}",
                f"{(this_week/weekly_limit*100):.1f}%"
            )
        
        with col3:
            monthly_limit = limit * 30
            st.metric(
                "This Month",
                f"{this_month}/{monthly_limit}",
                f"{(this_month/monthly_limit*100):.1f}%"
            )
        
        with col4:
            # Estimated cost if exceeded
            if this_month > monthly_limit:
                excess = this_month - monthly_limit
                cost = (excess / 1000) * 0.01
                st.metric(
                    "Est. Overage Cost",
                    f"${cost:.2f}",
                    "Over limit",
                    delta_color="inverse"
                )
            else:
                st.metric(
                    "Current Cost",
                    "$0.00",
                    "Within free tier"
                )
        
        st.write("---")
        
        # Usage graph
        st.subheader("📈 Daily Usage Trend")
        
        daily_usage = activity_df.groupby('Date').size().reset_index(name='Questions')
        daily_usage = daily_usage.tail(30)  # Last 30 days
        
        fig = px.line(
            daily_usage,
            x='Date',
            y='Questions',
            title='Questions per Day (Last 30 Days)'
        )
        
        # Add limit line
        fig.add_hline(
            y=limit,
            line_dash="dash",
            line_color="red",
            annotation_text="Daily Limit"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Warnings
        if today_questions > limit * 0.9:
            st.error(f"⚠️ WARNING: Approaching daily limit! ({today_questions}/{limit})")
        elif today_questions > limit * 0.7:
            st.warning(f"⚠️ High usage today: {today_questions}/{limit}")
        else:
            st.success(f"✅ Usage is healthy: {today_questions}/{limit}")
        
        # Top users today
        st.write("---")
        st.subheader("🔥 Most Active Students Today")
        
        today_activity = activity_df[activity_df['Date'] == today]
        if not today_activity.empty:
            top_today = today_activity['Student_Name'].value_counts().head(10)
            
            st.dataframe(
                pd.DataFrame({
                    'Student': top_today.index,
                    'Questions Today': top_today.values
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No activity today yet.")
    else:
        st.warning("No usage data available yet.")

if __name__ == "__main__":
    main()
