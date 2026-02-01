import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import quote
import json
import os

# Set page config
st.set_page_config(
    page_title="MBTI Personality Test", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem;
        font-size: 1.1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .result-box {
        padding: 2rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        text-align: center;
        margin: 2rem 0;
    }
    .question-image {
        display: block;
        margin: 2rem auto;
        max-width: 100%;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .question-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Load the data
@st.cache_data
def load_mbti_data():
    df = pd.read_excel('Updated_combinations.xlsx')
    return df

# Google Sheets connection
@st.cache_resource
def get_gsheet_connection():
    """Connect to Google Sheets using service account credentials"""
    try:
        # Load credentials from Streamlit secrets
        credentials_dict = st.secrets["gcp_service_account"]
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def save_to_google_sheets(data):
    """Save survey response to Google Sheets"""
    try:
        client = get_gsheet_connection()
        if client is None:
            return False
            
        # Open the spreadsheet by name (you'll need to create this)
        sheet_name = st.secrets.get("sheet_name", "MBTI_Survey_Responses")
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.sheet1
        
        # Append the data
        worksheet.append_row(list(data.values()))
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
        return False

def load_responses_from_sheets():
    """Load all responses from Google Sheets for analytics"""
    try:
        client = get_gsheet_connection()
        if client is None:
            return None
            
        sheet_name = st.secrets.get("sheet_name", "MBTI_Survey_Responses")
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.sheet1
        
        # Get all records
        data = worksheet.get_all_records()
        if data:
            return pd.DataFrame(data)
        return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Question mapping with image support
# To add images:
# 1. Upload image files to your GitHub repo in an 'images/' folder
# 2. Update 'image': 'images/q1.png' for each question
# OR use direct URLs: 'image': 'https://example.com/image.jpg'
questions = {
    'Q1': {
        'text': 'Do you focus more on...',
        'image': None,  # Example: 'images/q1.png' or 'https://example.com/image.jpg'
        'options': {'S': 'Facts and concrete details', 'N': 'Patterns and possibilities'}
    },
    'Q2': {
        'text': 'Do you get energy from...',
        'image': None,
        'options': {'E': 'Being with others', 'I': 'Spending time alone'}
    },
    'Q3': {
        'text': 'Do you prefer...',
        'image': None,
        'options': {'J': 'Structure and planning', 'P': 'Flexibility and spontaneity'}
    },
    'Q4': {
        'text': 'When making decisions, do you rely more on...',
        'image': None,
        'options': {'T': 'Logic and objectivity', 'F': 'Values and emotions'}
    },
    'Q5': {
        'text': 'Do you tend to...',
        'image': None,
        'options': {'J': 'Make decisions quickly', 'P': 'Keep options open'}
    },
    'Q6': {
        'text': 'Are you more...',
        'image': None,
        'options': {'E': 'Outgoing and expressive', 'I': 'Reserved and reflective'}
    },
    'Q7': {
        'text': 'Do you prefer...',
        'image': None,
        'options': {'S': 'Practical and realistic approaches', 'N': 'Imaginative and innovative ideas'}
    },
    'Q8': {
        'text': 'Do you value...',
        'image': None,
        'options': {'T': 'Fairness and consistency', 'F': 'Harmony and compassion'}
    },
    'Q9': {
        'text': 'When solving problems, do you focus on...',
        'image': None,
        'options': {'T': 'Rational analysis', 'F': 'How it affects people'}
    },
    'Q10': {
        'text': 'Do you like...',
        'image': None,
        'options': {'J': 'Having things settled', 'P': 'Adapting as you go'}
    },
    'Q11': {
        'text': 'In social situations, are you more...',
        'image': None,
        'options': {'E': 'Talkative and enthusiastic', 'I': 'Quiet and observant'}
    },
    'Q12': {
        'text': 'Do you trust...',
        'image': None,
        'options': {'S': 'Your experience and what you know', 'N': 'Your intuition and hunches'}
    }
}

# MBTI type descriptions
mbti_descriptions = {
    'ISTJ': 'The Inspector - Practical, fact-minded, and reliable',
    'ISFJ': 'The Protector - Warm-hearted, dedicated, and conscientious',
    'INFJ': 'The Counselor - Creative, insightful, and inspiring',
    'INTJ': 'The Mastermind - Strategic, analytical, and independent',
    'ISTP': 'The Craftsman - Bold, practical, and experimental',
    'ISFP': 'The Composer - Flexible, charming, and artistic',
    'INFP': 'The Healer - Idealistic, loyal, and compassionate',
    'INTP': 'The Architect - Innovative, curious, and logical',
    'ESTP': 'The Dynamo - Energetic, perceptive, and spontaneous',
    'ESFP': 'The Performer - Outgoing, friendly, and enthusiastic',
    'ENFP': 'The Champion - Enthusiastic, creative, and sociable',
    'ENTP': 'The Visionary - Inventive, strategic, and entrepreneurial',
    'ESTJ': 'The Supervisor - Organized, practical, and realistic',
    'ESFJ': 'The Provider - Caring, social, and popular',
    'ENFJ': 'The Teacher - Charismatic, inspiring, and altruistic',
    'ENTJ': 'The Commander - Bold, imaginative, and strong-willed'
}

def create_share_buttons(mbti_type, share_source="result_page"):
    """Create social media share buttons and track clicks"""
    
    # URLs for your app (you'll update this after deployment)
    app_url = "https://your-app-url.streamlit.app"  # UPDATE THIS AFTER DEPLOYMENT
    share_text = f"I just discovered I'm an {mbti_type}! Take the MBTI personality test and find out your type:"
    
    st.markdown("### 📢 Share Your Results!")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        twitter_url = f"https://twitter.com/intent/tweet?text={quote(share_text)}&url={quote(app_url)}"
        if st.button("🐦 Share on Twitter"):
            track_share("Twitter", mbti_type, share_source)
            st.markdown(f'<a href="{twitter_url}" target="_blank">Click here if not redirected</a>', unsafe_allow_html=True)
            st.write("Opening Twitter...")
    
    with col2:
        linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={quote(app_url)}"
        if st.button("💼 Share on LinkedIn"):
            track_share("LinkedIn", mbti_type, share_source)
            st.markdown(f'<a href="{linkedin_url}" target="_blank">Click here if not redirected</a>', unsafe_allow_html=True)
            st.write("Opening LinkedIn...")
    
    with col3:
        whatsapp_url = f"https://wa.me/?text={quote(share_text + ' ' + app_url)}"
        if st.button("💬 Share on WhatsApp"):
            track_share("WhatsApp", mbti_type, share_source)
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">Click here if not redirected</a>', unsafe_allow_html=True)
            st.write("Opening WhatsApp...")
    
    with col4:
        email_url = f"mailto:?subject=Check out this MBTI Test&body={quote(share_text + ' ' + app_url)}"
        if st.button("📧 Share via Email"):
            track_share("Email", mbti_type, share_source)
            st.markdown(f'<a href="{email_url}" target="_blank">Click here if not redirected</a>', unsafe_allow_html=True)
            st.write("Opening Email...")

def track_share(platform, mbti_type, source):
    """Track share button clicks to Google Sheets"""
    try:
        client = get_gsheet_connection()
        if client is None:
            return
            
        sheet_name = st.secrets.get("sheet_name", "MBTI_Survey_Responses")
        spreadsheet = client.open(sheet_name)
        
        # Try to get or create the 'Shares' worksheet
        try:
            shares_sheet = spreadsheet.worksheet("Shares")
        except:
            # Create it if it doesn't exist
            shares_sheet = spreadsheet.add_worksheet(title="Shares", rows="1000", cols="5")
            shares_sheet.append_row(["Timestamp", "Platform", "MBTI_Type", "Source", "URL"])
        
        # Add share data
        share_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            platform,
            mbti_type,
            source,
            "your-app-url.streamlit.app"  # UPDATE THIS
        ]
        shares_sheet.append_row(share_data)
    except Exception as e:
        st.error(f"Error tracking share: {e}")

def initialize_session_state():
    """Initialize session state variables"""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0  # 0 = demographics, 1-12 = questions, 13 = results
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if 'demographics' not in st.session_state:
        st.session_state.demographics = {}
    if 'survey_complete' not in st.session_state:
        st.session_state.survey_complete = False
    if 'mbti_result' not in st.session_state:
        st.session_state.mbti_result = None

def show_progress():
    """Display progress bar"""
    total_steps = 13  # 1 demographics + 12 questions
    current = st.session_state.current_step
    progress = current / total_steps
    
    st.progress(progress)
    if current == 0:
        st.caption("📋 Demographics")
    elif current <= 12:
        st.caption(f"Question {current} of 12")
    else:
        st.caption("✅ Complete!")

def demographics_page():
    """Show demographics collection page"""
    st.title("🧠 MBTI Personality Test")
    st.markdown("### Welcome! Let's start with a few details about you.")
    
    show_progress()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.selectbox(
            "Age Range",
            ["Prefer not to say", "Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
            key="age_select"
        )
        
        gender = st.selectbox(
            "Gender",
            ["Prefer not to say", "Male", "Female", "Non-binary", "Other"],
            key="gender_select"
        )
    
    with col2:
        country = st.text_input("Country (optional)", key="country_input", placeholder="e.g., United States")
        
        occupation = st.selectbox(
            "Occupation",
            ["Prefer not to say", "Student", "Professional", "Self-employed", "Retired", "Unemployed", "Other"],
            key="occupation_select"
        )
    
    referral_source = st.selectbox(
        "How did you hear about this test?",
        ["Select one", "Social Media", "Friend/Family", "Search Engine", "Website/Blog", "Other"],
        key="referral_select"
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("▶️ Start Survey", use_container_width=True, type="primary"):
            # Save demographics
            st.session_state.demographics = {
                'age': age,
                'gender': gender,
                'country': country if country else "Not specified",
                'occupation': occupation,
                'referral_source': referral_source
            }
            st.session_state.current_step = 1
            st.rerun()

def question_page(question_num):
    """Show individual question page"""
    q_id = f'Q{question_num}'
    q_data = questions[q_id]
    
    st.title("🧠 MBTI Personality Test")
    
    show_progress()
    
    st.markdown("---")
    
    # Question container
    st.markdown('<div class="question-container">', unsafe_allow_html=True)
    
    # Question text
    st.markdown(f"### {q_data['text']}")
    
    # Image (if provided)
    if q_data['image']:
        if q_data['image'].startswith('http'):
            # URL image
            st.markdown(f'<img src="{q_data["image"]}" class="question-image" />', unsafe_allow_html=True)
        else:
            # Local file
            if os.path.exists(q_data['image']):
                st.image(q_data['image'], use_container_width=True)
            else:
                st.info(f"Image not found: {q_data['image']}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Answer options
    st.markdown("### Choose one:")
    
    # Get current answer if exists
    current_answer = st.session_state.answers.get(q_id)
    
    # Create radio buttons
    answer = st.radio(
        "Select your answer:",
        options=list(q_data['options'].keys()),
        format_func=lambda x: q_data['options'][x],
        index=list(q_data['options'].keys()).index(current_answer) if current_answer else 0,
        key=f"radio_{q_id}",
        label_visibility="collapsed"
    )
    
    # Save answer
    st.session_state.answers[q_id] = answer
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if question_num > 1:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_step -= 1
                st.rerun()
    
    with col3:
        if question_num < 12:
            if st.button("Next ➡️", use_container_width=True, type="primary"):
                st.session_state.current_step += 1
                st.rerun()
        else:
            if st.button("🎯 Get Results", use_container_width=True, type="primary"):
                calculate_and_save_result()
                st.rerun()

def calculate_and_save_result():
    """Calculate MBTI result and save to Google Sheets"""
    try:
        df = load_mbti_data()
    except FileNotFoundError:
        st.error("⚠️ Excel file 'Updated_combinations.xlsx' not found.")
        return
    
    # Look up MBTI type
    mask = pd.Series([True] * len(df))
    for q_id, answer in st.session_state.answers.items():
        mask &= (df[q_id] == answer)
    
    result = df[mask]
    
    if len(result) > 0:
        mbti_type = result.iloc[0]['MBTI Type']
        
        # Prepare data for Google Sheets
        survey_data = {
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Age': st.session_state.demographics['age'],
            'Gender': st.session_state.demographics['gender'],
            'Country': st.session_state.demographics['country'],
            'Occupation': st.session_state.demographics['occupation'],
            'Referral_Source': st.session_state.demographics['referral_source'],
            **st.session_state.answers,  # Add all Q1-Q12 answers
            'E_I': result.iloc[0]['E/I'],
            'S_N': result.iloc[0]['S/N'],
            'T_F': result.iloc[0]['T/F'],
            'J_P': result.iloc[0]['J/P'],
            'MBTI_Type': mbti_type
        }
        
        # Save to Google Sheets
        saved = save_to_google_sheets(survey_data)
        
        # Store result
        st.session_state.mbti_result = {
            'type': mbti_type,
            'dimensions': {
                'E_I': result.iloc[0]['E/I'],
                'S_N': result.iloc[0]['S/N'],
                'T_F': result.iloc[0]['T/F'],
                'J_P': result.iloc[0]['J/P']
            },
            'saved': saved
        }
        st.session_state.survey_complete = True
        st.session_state.current_step = 13

def show_results():
    """Display survey results"""
    if not st.session_state.mbti_result:
        st.error("No results available")
        return
    
    mbti_type = st.session_state.mbti_result['type']
    dimensions = st.session_state.mbti_result['dimensions']
    saved = st.session_state.mbti_result['saved']
    description = mbti_descriptions.get(mbti_type, 'No description available')
    
    st.title("🧠 MBTI Personality Test")
    
    if saved:
        st.success("✅ Your response has been saved successfully!")
    else:
        st.warning("⚠️ Could not save to database, but here are your results:")
    
    st.markdown("## 🎉 Your Result")
    st.markdown(f"""
    <div class="result-box">
        <h1 style="color: #4CAF50; margin-bottom: 0.5rem;">{mbti_type}</h1>
        <h3 style="color: #555; margin-top: 0;">{description}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Show the breakdown
    st.markdown("### 📊 Your Profile Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("E/I", dimensions['E_I'])
        st.caption("Extraversion vs Introversion")
    with col2:
        st.metric("S/N", dimensions['S_N'])
        st.caption("Sensing vs Intuition")
    with col3:
        st.metric("T/F", dimensions['T_F'])
        st.caption("Thinking vs Feeling")
    with col4:
        st.metric("J/P", dimensions['J_P'])
        st.caption("Judging vs Perceiving")
    
    st.markdown("---")
    
    # Share buttons
    create_share_buttons(mbti_type)
    
    st.markdown("---")
    
    # Retake button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Retake Test", use_container_width=True):
            # Reset everything
            st.session_state.current_step = 0
            st.session_state.answers = {}
            st.session_state.demographics = {}
            st.session_state.survey_complete = False
            st.session_state.mbti_result = None
            st.rerun()

def survey_page():
    """Main survey page controller"""
    initialize_session_state()
    
    # Route to appropriate page based on current step
    if st.session_state.current_step == 0:
        demographics_page()
    elif 1 <= st.session_state.current_step <= 12:
        question_page(st.session_state.current_step)
    elif st.session_state.current_step == 13:
        show_results()

def analytics_page():
    """Analytics dashboard page"""
    st.title("📊 Analytics Dashboard")
    st.markdown("### Survey Statistics & Insights")
    
    # Load data from Google Sheets
    with st.spinner("Loading analytics data..."):
        df = load_responses_from_sheets()
    
    if df is None or len(df) == 0:
        st.info("📭 No survey responses yet. Share your survey to start collecting data!")
        return
    
    # Overview metrics
    st.markdown("## 📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Responses", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        unique_types = df['MBTI_Type'].nunique()
        st.metric("Unique MBTI Types", unique_types)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        most_common = df['MBTI_Type'].mode()[0] if len(df) > 0 else "N/A"
        st.metric("Most Common Type", most_common)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        today_responses = len(df[pd.to_datetime(df['Timestamp']).dt.date == datetime.now().date()])
        st.metric("Today's Responses", today_responses)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # MBTI Type Distribution
    st.markdown("## 🎯 MBTI Type Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        type_counts = df['MBTI_Type'].value_counts()
        fig_pie = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="MBTI Types Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart
        fig_bar = px.bar(
            x=type_counts.index,
            y=type_counts.values,
            title="MBTI Types Count",
            labels={'x': 'MBTI Type', 'y': 'Count'},
            color=type_counts.values,
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # Dimension Analysis
    st.markdown("## 🔍 Dimension Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    
    dimensions = [
        ('E_I', 'E vs I', col1),
        ('S_N', 'S vs N', col2),
        ('T_F', 'T vs F', col3),
        ('J_P', 'J vs P', col4)
    ]
    
    for dim_col, dim_name, col in dimensions:
        with col:
            dim_counts = df[dim_col].value_counts()
            fig = px.pie(
                values=dim_counts.values,
                names=dim_counts.index,
                title=dim_name,
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Demographics Analysis
    st.markdown("## 👥 Demographics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Age distribution
        age_counts = df['Age'].value_counts()
        fig_age = px.bar(
            x=age_counts.index,
            y=age_counts.values,
            title="Age Distribution",
            labels={'x': 'Age Range', 'y': 'Count'},
            color=age_counts.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_age, use_container_width=True)
    
    with col2:
        # Gender distribution
        gender_counts = df['Gender'].value_counts()
        fig_gender = px.pie(
            values=gender_counts.values,
            names=gender_counts.index,
            title="Gender Distribution",
            hole=0.3
        )
        st.plotly_chart(fig_gender, use_container_width=True)
    
    # Occupation
    st.markdown("### 💼 Occupation Distribution")
    occupation_counts = df['Occupation'].value_counts()
    fig_occupation = px.bar(
        x=occupation_counts.index,
        y=occupation_counts.values,
        title="Occupation Breakdown",
        labels={'x': 'Occupation', 'y': 'Count'},
        color=occupation_counts.values,
        color_continuous_scale='Greens'
    )
    st.plotly_chart(fig_occupation, use_container_width=True)
    
    st.markdown("---")
    
    # Question Analysis
    st.markdown("## 📝 Question Response Analysis")
    
    question_cols = [f'Q{i}' for i in range(1, 13)]
    
    # Create a grid of small charts
    cols_per_row = 3
    for i in range(0, len(question_cols), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(question_cols):
                q_col = question_cols[i + j]
                with cols[j]:
                    q_counts = df[q_col].value_counts()
                    fig = px.pie(
                        values=q_counts.values,
                        names=q_counts.index,
                        title=f"{q_col} Responses",
                        hole=0.3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Timeline
    st.markdown("## 📅 Response Timeline")
    df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
    daily_counts = df.groupby('Date').size().reset_index(name='Responses')
    
    fig_timeline = px.line(
        daily_counts,
        x='Date',
        y='Responses',
        title="Daily Response Count",
        markers=True
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    st.markdown("---")
    
    # Referral Source
    st.markdown("## 🔗 Referral Sources")
    referral_counts = df['Referral_Source'].value_counts()
    fig_referral = px.bar(
        x=referral_counts.index,
        y=referral_counts.values,
        title="How People Found This Survey",
        labels={'x': 'Source', 'y': 'Count'},
        color=referral_counts.values,
        color_continuous_scale='Purples'
    )
    st.plotly_chart(fig_referral, use_container_width=True)
    
    # Download data option
    st.markdown("---")
    st.markdown("## 💾 Export Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Full Dataset (CSV)",
        data=csv,
        file_name=f"mbti_survey_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def main():
    # Sidebar navigation
    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["📝 Take Survey", "📊 View Analytics"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "This MBTI personality test helps you discover your personality type "
        "through 12 carefully designed questions. Each question is presented "
        "on its own page for a better experience. Share your results and "
        "view analytics to see how you compare with others!"
    )
    
    # Page routing
    if page == "📝 Take Survey":
        survey_page()
    else:
        analytics_page()

if __name__ == "__main__":
    main()
