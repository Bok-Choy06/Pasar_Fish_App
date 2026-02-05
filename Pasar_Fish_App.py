import base64
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
    page_title="Which Local Fish Are You?", 
    page_icon="🐟", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Force all images to be reasonable sizes */
    img {
        max-width: 100% !important;
        height: auto !important;
        object-fit: contain !important;
    }
    
    /* Main container */
    .main {
        padding: 1rem;
        max-width: 100%;
    }
    
    /* Desktop - constrain image sizes */
    @media (min-width: 769px) {
        .main img {
            max-width: 500px !important;
            max-height: 400px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            display: block !important;
        }
    }
    
    /* Mobile - smaller images */
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }
        .main img {
            max-width: 280px !important;
            max-height: 280px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            display: block !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h3 {
            font-size: 1.2rem !important;
        }
    }
    
    /* Constrain the white background boxes */
    .main > div > div > div {
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
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
        margin: 1rem auto;
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

# Add Font Awesome for brand icons
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
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
        'text': '“Psst! Over here!” You turn to see a strange looking fish on a mural talking to you as you walk through the wet market. “Wanna go on an adventure with me?',
        'image': 'images/Q1.png',
        'options': {'S': 'Wait… did that fish painting just speak to me', 'N': 'An adventure? That sounds fun!'}
    },
    'Q2': {
        'text': 'Before you can answer, you are swept away by a magical wave. When you open your eyes, you find yourself standing on a coast with wooden sampans docked at the edge of the water. A group of people with Bubu (woven rattan) fish traps, spears, nets, and fishing handlines stand around the boats.',
        'image': 'images/Q2.png',
        'options': {'E': 'I should ask them for help and information! They seem like they know where we are.', 'I': 'Let me observe them first before approaching, what if they’re dangerous?'}
    },
    'Q3': {
        'text': 'After introducing yourself to the group and explaining your situation, the group introduces themselves as Orang Lauts (Sea People). They invite you to join them on their fishing trip in exchange for finding you a way home later. You hop onto one of their boats and look through the many fishing gear they have.',
        'image': 'images/Q3.png',
        'options': {'J': "Let's see… which would help me easily catch the most fish?", 'P': "Woah! I have so many options to try out!"}
    },
    'Q4': {
        'text': 'As the Orang Laut row forward, you look down into the water and see that strange looking fish again swimming alongside your boat. It gives you a playful wink before disappearing, and you hear someone shout “Brace Yourselves!”. A storm approaches the boats and the waves start to shake them violently.',
        'image': 'images/Q4.png',
        'options': {'T': 'Secure all the fishing gear! Let’s find a way to make sure our boat does not capsize.', 'F': 'I hope no one gets injured or falls overboard!'}
    },
    'Q5': {
        'text': 'You feel yourself get thrown overboard! You shut your eyes tight expecting to feel a rush of cold sea water hit your body, but you crash onto a hard surface with a loud thud instead. “Oi, stop sleeping and get back to work.” You open your eyes and find yourself laying on the wooden planks of a kelong and a fisherman standing over you.',
        'image': 'images/Q5.png',
        'options': {'J': 'Back to work? Can’t I explore this new place a bit first to see where or when I am?', 'P': 'Okay, tell me what I need to do so I can maybe find a way back to my timeline.'}
    },
    'Q6': {
        'text': '“Come help me feed the fish,” the fisherman says before handing you a bag of fish food. You take the bag and begin to throw fish food into the cage-nets filled with hungry groupers with the fisherman. It almost feels… peaceful.',
        'image': 'images/Q6.png',
        'options': {'E': 'Talk to the fisherman about your strange adventure so far and his life on the kelong.', 'I': 'Enjoy the peacefulness and silence while feeding the fish.'}
    },
    'Q7': {
        'text': 'As you feed the fish you see a glowing light appear in the cage-net closest to you. “BOO!” You jump in shock as the strange fish pops up amongst the groupers and scares you. Losing your balance, you fall into the cage-net with a big splash!',
        'image': 'images/Q7.png',
        'options': {'S': 'You’ve gotta be kidding me… Why is this happening to me and how do I get out of this net?', 'N': 'Maybe I’ll be transported again just like before! Where will I go this time?'}
    },
    'Q8': {
        'text': 'The groupers in the cage-net begin to swim frantically and the splashing water causes you to close your eyes. You feel a push that causes you to fly up into the air. You brace yourself for the impact of the hard wooden floor, but you feel yourself landing onto something softer. “OW! What even…” You hear someone exclaim from under you.',
        'image': 'images/Q8.png',
        'options': {'T': 'How did this happen? Where am I and did I injure this person?', 'F': 'Oh my god, I’m so sorry are you okay? I didn’t mean to do that, I’m sorry!'}
    },
    'Q9': {
        'text': 'You stand up and help the person up from the wet, slippery, concrete ground. As the smell of fish surrounds you, you look around and see multiple stacks of crates in a variety of sizes and colours and fish mongers preparing and selling many types of fish. The person introduces themselves as a fish monger in Jurong Fishery Port and excitedly offers you a tour.',
        'image': 'images/Q9.png',
        'options': {'T': 'Oh, Jurong! I know how to get home from here!', 'F': 'I feel like going home, but I think I’ll stay for a short tour since they’re excited to give me one!'}
    },
    'Q10': {
        'text': 'The fish monger takes you on a tour around the fishery port, sharing that Singapore imports their fish from countries such as Malaysia, Indonesia, Vietnam, and other countries. As he shares that fish from our local fish farms are sometimes sold here as well, something moving in the crate of ice catches your eye. It’s that strange fish again!',
        'image': 'images/Q10.png',
        'options': {'J': 'Uh oh… Here we go again. At least tell me where we’re going first.', 'P': 'Oh, is it time to leave here now? Okay, I’m ready!'}
    },
    'Q11': {
        'text': '“Watch out!” You hear the fish monger shout. You turn to see a giant crate of ice at the top of the stack crashing down onto you. You squeeze your eyes shut in terror and anticipation, but nothing hits you. “Hey, you okay?” You open your eyes and see someone in front of you and giant tanks filled with a variety of fish with high-tech equipment in the area. The person in front introduces themselves as one of the local fish farmers.',
        'image': 'images/Q11.png',
        'options': {'E': 'You will not believe what I’ve gone through today [Begin sharing what has happened]', 'I': 'Oh, I’m okay, nice to meet you.'}
    },
    'Q12': {
        'text': 'The fish farmer gives you a tour of the fish farm where Barramundi (or Asian Seabass) and red snappers are cultivated using cutting-edge technology that controls feed, oxygen levels and waste. “Weeeeeee!” You hear a voice above you getting louder and look up to see the strange fish plummeting down from the sky. You catch the strange fish in your arms and it jumps at your face. You shut your eyes before opening them to find yourself finally back at the wet market.',
        'image': 'images/Q12.png',
        'options': {'S': 'Yay I’m finally back! Was all of that real? How did I do that?', 'N': 'That was so fun! I wonder why that fish made me experience those timelines and places.'}
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

# Fish image mapping - NEW DICTIONARY (ADD THIS)
fish_images = {
    'ISTJ': 'images/Malabar_Red_Snapper.jpg',
    'ISFJ': 'images/Anchovy.jpg',
    'INFJ': 'images/Brownbanded_Bamboo_Shark.jpg',
    'INTJ': 'images/Diamond_Trevally.jpg',
    'ISTP': 'images/Unicorn_Leatherjacket.jpg',
    'ISFP': 'images/Barramundi.jpg',
    'INFP': 'images/Bombay_Duck.jpg',
    'INTP': 'images/Whitespotted_Whipray.jpg',
    'ESTP': 'images/Narrow_Based Spanish Mackerel.jpg',
    'ESFP': 'images/Black_Promfret.jpg',
    'ENFP': 'images/Yellowtail_Fusilier.jpg',
    'ENTP': 'images/Indian_Mackerel.jpg',
    'ESTJ': 'images/Wolf_Herring.jpg',
    'ESFJ': 'images/Yellowtail_Croaker.jpg',
    'ENFJ': 'images/Longtailed_Tuna.jpg',
    'ENTJ': 'images/Giant_Grouper.jpg'
}

# Fish names mapping - extracted from filenames
fish_names = {
    'ISTJ': 'Malabar Red Snapper',
    'ISFJ': 'Anchovy',
    'INFJ': 'Brownbanded Bamboo Shark',
    'INTJ': 'Diamond Trevally',
    'ISTP': 'Unicorn Leatherjacket',
    'ISFP': 'Barramundi',
    'INFP': 'Bombay Duck',
    'INTP': 'Whitespotted Whipray',
    'ESTP': 'Narrow-Based Spanish Mackerel',
    'ESFP': 'Black Pomfret',
    'ENFP': 'Yellowtail Fusilier',
    'ENTP': 'Indian Mackerel',
    'ESTJ': 'Wolf Herring',
    'ESFJ': 'Yellowtail Croaker',
    'ENFJ': 'Longtailed Tuna',
    'ENTJ': 'Giant Grouper'
}

# List of countries for dropdown
countries = [
    "", "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", 
    "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", 
    "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", 
    "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", 
    "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", 
    "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", 
    "Dominican Republic", "East Timor", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", 
    "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", 
    "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", 
    "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", 
    "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea North", "Korea South", "Kosovo", 
    "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", 
    "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", 
    "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", 
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", 
    "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Macedonia", "Norway", "Oman", "Pakistan", 
    "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", 
    "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", 
    "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", 
    "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", 
    "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", 
    "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Togo", "Tonga", 
    "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", 
    "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", 
    "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
]

def create_share_buttons(mbti_type, share_source="result_page"):
    """Create social media share buttons - all in white box"""
    
    app_url = "https://pasarfishapp-eu7kqgndtsmiy9pwfz9zrr.streamlit.app/"
    fish_name = fish_names.get(mbti_type, mbti_type)
    share_text_with_url = "I just discovered I'm a " + fish_name + " 🐟. Take the Pasar Fish quiz today to find out which local fish matches your personality!\n" + app_url
    share_text = "I just discovered I'm a " + fish_name + " 🐟. Take the Pasar Fish quiz today to find out which local fish matches your personality!"
    
    x_url = "https://twitter.com/intent/tweet?text=" + quote(share_text_with_url)
    linkedin_url = "https://www.linkedin.com/sharing/share-offsite/?url=" + quote(app_url)
    whatsapp_url = "https://wa.me/?text=" + quote(share_text_with_url)
    telegram_url = "https://t.me/share/url?url=" + quote(app_url) + "&text=" + quote(share_text)
    
    st.markdown("""
        <div style="background-color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 2rem auto; max-width: 900px;">
            <h3 style="text-align: center; color: #333; margin-bottom: 2rem;">📢 Share Your Results!</h3>
            <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 2rem; padding: 1rem;">
                <div style="text-align: center;">
                    <a href="https://www.instagram.com/" target="_blank">
                        <i class="fab fa-instagram" style="font-size: 48px; color: #E4405F;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + x_url + """" target="_blank">
                        <i class="fab fa-x-twitter" style="font-size: 48px; color: #000000;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + linkedin_url + """" target="_blank">
                        <i class="fab fa-linkedin" style="font-size: 48px; color: #0077B5;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + whatsapp_url + """" target="_blank">
                        <i class="fab fa-whatsapp" style="font-size: 48px; color: #25D366;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + telegram_url + """" target="_blank">
                        <i class="fab fa-telegram" style="font-size: 48px; color: #0088cc;"></i>
                    </a>
                </div>
            </div>
            <div style="text-align: center; margin-top: 1rem; color: #888; font-size: 12px;">
                💡 Click icons to share! For Instagram, screenshot this page.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
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
    
    # Time tracking
    if 'start_time' not in st.session_state:
        st.session_state.start_time = datetime.now()
    if 'question_start_times' not in st.session_state:
        st.session_state.question_start_times = {}
    if 'question_durations' not in st.session_state:
        st.session_state.question_durations = {}
    if 'page_start_time' not in st.session_state:
        st.session_state.page_start_time = datetime.now()

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
    
    # Center-aligned title
    st.markdown("""
        <h1 style="text-align: center;">🐟 Which Local Fish Are You?</h1>
    """, unsafe_allow_html=True)
    
    # Function to convert image to base64
    def get_image_base64(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    
    # Find and encode the image
    image_path = None
    if os.path.exists('Pasar Fish.png'):
        image_path = 'Pasar Fish.png'
    elif os.path.exists('images/Pasar Fish.png'):
        image_path = 'images/Pasar Fish.png'
    elif os.path.exists('Pasar Fish.jpg'):
        image_path = 'Pasar Fish.jpg'
    elif os.path.exists('images/Pasar Fish.jpg'):
        image_path = 'images/Pasar Fish.jpg'
    
    if image_path:
        img_base64 = get_image_base64(image_path)
        img_extension = 'png' if image_path.endswith('.png') else 'jpeg'
        
        st.markdown(f"""
            <div style="background-color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 2rem auto; max-width: 700px; text-align: center;">
                <img src="data:image/{img_extension};base64,{img_base64}" 
                     style="max-width: 100%; height: auto; border-radius: 10px;" 
                     alt="Pasar Fish">
            </div>
        """, unsafe_allow_html=True)
    
    # Center-aligned text
    st.markdown("""
        <h3 style="text-align: center;">Embark on a journey through time and markets to discover your inner fishy personality!</h3>
        <h4 style="text-align: center;">Let's start with a few details about you.</h4>
    """, unsafe_allow_html=True)
    
    show_progress()
    
    # Track page start time (only set once per page load)
    if 'demographics_start_time' not in st.session_state:
        st.session_state.demographics_start_time = datetime.now()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.selectbox(
            "Age Range *",
            ["Select an option", "Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
            key="age_select"
        )
        
        gender = st.selectbox(
            "Gender *",
            ["Select an option", "Male", "Female", "Non-binary", "Other", "Prefer not to say"],
            key="gender_select"
        )
    
    with col2:
        # Searchable country dropdown
        country = st.selectbox(
            "Country (optional)",
            countries,
            key="country_input"
        )
        
        occupation = st.selectbox(
            "Occupation *",
            ["Select an option", "Student", "Professional", "Self-employed", "Retired", "Unemployed", "Other"],
            key="occupation_select"
        )
    
    referral_source = st.selectbox(
        "How did you hear about this test? *",
        ["Select an option", "Social Media", "Friend/Family", "Search Engine", "Website/Blog", "Other"],
        key="referral_select"
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🐟 Start Quiz", use_container_width=True, type="primary"):
            # Validation
            if age == "Select an option":
                st.error("❌ Please select your age range")
                return
            if gender == "Select an option":
                st.error("❌ Please select your gender")
                return
            if occupation == "Select an option":
                st.error("❌ Please select your occupation")
                return
            if referral_source == "Select an option":
                st.error("❌ Please tell us how you heard about this test")
                return
            
            # Calculate time spent on demographics
            demographics_duration = (datetime.now() - st.session_state.demographics_start_time).total_seconds()
            
            # Save demographics
            st.session_state.demographics = {
                'age': age,
                'gender': gender,
                'country': country if country else "Not specified",
                'occupation': occupation,
                'referral_source': referral_source,
                'demographics_time': round(demographics_duration, 2)
            }
            
            # Set start time for first question
            st.session_state.question_start_times['Q1'] = datetime.now()
            st.session_state.current_step = 1
            st.rerun()

def question_page(question_num):
    """Show individual question page"""
    q_id = f'Q{question_num}'
    q_data = questions[q_id]
    
    # Set start time for this question if not already set
    if q_id not in st.session_state.question_start_times:
        st.session_state.question_start_times[q_id] = datetime.now()
    
    st.title("🐟 Which Local Fish Are You?")
    
    show_progress()
    
    st.markdown("---")
    
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
                # FIX 1 (Part B): Changed use_container_width=True to a fixed width
                # 350-400px is usually a good size to avoid scrolling
                st.image(q_data['image'], width=600) 
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
                # Record time spent on current question before going back
                if q_id in st.session_state.question_start_times:
                    duration = (datetime.now() - st.session_state.question_start_times[q_id]).total_seconds()
                    # Only update if this is the first time recording or going back
                    if q_id not in st.session_state.question_durations:
                        st.session_state.question_durations[q_id] = round(duration, 2)
                
                st.session_state.current_step -= 1
                prev_q_id = f'Q{question_num - 1}'
                # Reset start time for previous question
                st.session_state.question_start_times[prev_q_id] = datetime.now()
                st.rerun()
    
    with col3:
        if question_num < 12:
            if st.button("Next ➡️", use_container_width=True, type="primary"):
                # Record time spent on current question
                if q_id in st.session_state.question_start_times:
                    duration = (datetime.now() - st.session_state.question_start_times[q_id]).total_seconds()
                    st.session_state.question_durations[q_id] = round(duration, 2)
                
                # Set start time for next question
                next_q_id = f'Q{question_num + 1}'
                st.session_state.question_start_times[next_q_id] = datetime.now()
                
                st.session_state.current_step += 1
                st.rerun()
        else:
            if st.button("🎯 Get Results", use_container_width=True, type="primary"):
                # Record time spent on final question
                if q_id in st.session_state.question_start_times:
                    duration = (datetime.now() - st.session_state.question_start_times[q_id]).total_seconds()
                    st.session_state.question_durations[q_id] = round(duration, 2)
                
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
        
        # Calculate total survey time
        total_time = (datetime.now() - st.session_state.start_time).total_seconds()
        
        # Get individual question times (with defaults for any missing)
        question_times = {}
        for i in range(1, 13):
            q_id = f'Q{i}'
            question_times[f'{q_id}_Time'] = st.session_state.question_durations.get(q_id, 0)
        
        # Prepare data for Google Sheets
        survey_data = {
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Age': st.session_state.demographics['age'],
            'Gender': st.session_state.demographics['gender'],
            'Country': st.session_state.demographics['country'],
            'Occupation': st.session_state.demographics['occupation'],
            'Referral_Source': st.session_state.demographics['referral_source'],
            'Demographics_Time': st.session_state.demographics.get('demographics_time', 0),
            **st.session_state.answers,  # Add all Q1-Q12 answers
            **question_times,  # Add all Q1_Time through Q12_Time
            'Total_Survey_Time': round(total_time, 2),
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
            'saved': saved,
            'total_time': round(total_time, 2),
            'question_times': question_times
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
    total_time = st.session_state.mbti_result.get('total_time', 0)
    description = mbti_descriptions.get(mbti_type, 'No description available')
    
    st.title("🐟 Which Local Fish Are You?")
    
    if saved:
        st.success("✅ Your response has been saved successfully!")
    else:
        st.warning("⚠️ Could not save to database, but here are your results:")
    
    # Show completion time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    if minutes > 0:
        time_str = f"{minutes} min {seconds} sec"
    else:
        time_str = f"{seconds} sec"
    
    st.info(f"⏱️ Completed in: {time_str}")
    
    st.markdown("## 🎉 Your Fish!")
    
    # Display fish image instead of MBTI type text
    fish_image_path = fish_images.get(mbti_type)
    
    if fish_image_path and os.path.exists(fish_image_path):
        # Center the fish image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(fish_image_path, use_container_width=True)
    else:
        # Fallback if image doesn't exist
        st.markdown(f"""
        <div class="result-box">
            <h1 style="color: #4CAF50; margin-bottom: 0.5rem;">{mbti_type}</h1>
            <h3 style="color: #555; margin-top: 0;">{description}</h3>
            <p style="color: #888;">Fish image not found. Please upload: {fish_image_path}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Follow Links Section - ALL content in one white box
    st.markdown("""
        <div style="background-color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 2rem 0;">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h3 style="color: #333; margin-bottom: 0.5rem;">🌐 Follow Pasar Fish!</h3>
                <p style="color: #666;">Stay connected with us for more fishy adventures:</p>
            </div>
            <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 2rem;">
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://pasarfish.com" target="_blank" style="text-decoration: none;">
                        <i class="fas fa-globe" style="font-size: 32px; color: #4CAF50;"></i>
                        <br><br>
                        <span style="font-size: 14px; color: #4A90E2;">Pasarfish.com</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://instagram.com/pasarfishsg" target="_blank" style="text-decoration: none;">
                        <i class="fab fa-instagram" style="font-size: 32px; color: #E4405F;"></i>
                        <br><br>
                        <span style="font-size: 14px; color: #4A90E2;">@Pasarfishsg</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://linkedin.com/company/pasarfish" target="_blank" style="text-decoration: none;">
                        <i class="fab fa-linkedin" style="font-size: 32px; color: #0077B5;"></i>
                        <br><br>
                        <span style="font-size: 14px; color: #4A90E2;">@Pasarfish</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://www.facebook.com/p/Pasarfishsg-61568193013803/" target="_blank" style="text-decoration: none;">
                        <i class="fab fa-facebook" style="font-size: 32px; color: #1877F2;"></i>
                        <br><br>
                        <span style="font-size: 14px; color: #4A90E2;">@Pasarfishsg</span>
                    </a>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Share buttons (existing code continues here)
    
    st.markdown("---")
    
    # Share buttons
    create_share_buttons(mbti_type)
    
    st.markdown("---")
    
    # Retake button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Retake Quiz", use_container_width=True):
            # Reset everything
            st.session_state.current_step = 0
            st.session_state.answers = {}
            st.session_state.demographics = {}
            st.session_state.survey_complete = False
            st.session_state.mbti_result = None
            st.session_state.start_time = datetime.now()
            st.session_state.question_start_times = {}
            st.session_state.question_durations = {}
            if 'demographics_start_time' in st.session_state:
                del st.session_state.demographics_start_time
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
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>📊 Pasarfish Analytics Dashboard</h1>
            <h3>For All Your Fish Quiz Statistics & Insights!</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Load data from Google Sheets
    with st.spinner("Loading analytics data..."):
        df = load_responses_from_sheets()
    
    if df is None or len(df) == 0:
        st.info("📭 No quiz responses yet. Share your fish quiz to start collecting data! 🐟")
        return
    
    # Overview metrics
    st.markdown("## 📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Responses", len(df))
    
    with col2:
        unique_types = df['MBTI_Type'].nunique()
        st.metric("Unique Fish Types", unique_types)
    
    with col3:
        most_common = df['MBTI_Type'].mode()[0] if len(df) > 0 else "N/A"
        st.metric("Most Common Fish", most_common)
    
    with col4:
        today_responses = len(df[pd.to_datetime(df['Timestamp']).dt.date == datetime.now().date()])
        st.metric("Today's Responses", today_responses)
    
    st.markdown("---")
    
    # MBTI Type Distribution
    st.markdown("## 🎯 Fish Type Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        type_counts = df['MBTI_Type'].value_counts()
        fig_pie = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Fish Types Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart
        fig_bar = px.bar(
            x=type_counts.index,
            y=type_counts.values,
            title="Fish Types Count",
            labels={'x': 'Fish Type', 'y': 'Count'},
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

    st.markdown("---")
    
    # Time Analytics Section
    st.markdown("## ⏱️ Time Analytics")
    
    # Check if time columns exist in the data
    time_cols_exist = 'Total_Survey_Time' in df.columns
    
    if time_cols_exist:
        # Overall time statistics
        st.markdown("### 📊 Survey Completion Time")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_time = df['Total_Survey_Time'].mean()
            st.metric("Average Time", f"{int(avg_time // 60)}m {int(avg_time % 60)}s")
        
        with col2:
            median_time = df['Total_Survey_Time'].median()
            st.metric("Median Time", f"{int(median_time // 60)}m {int(median_time % 60)}s")
        
        with col3:
            min_time = df['Total_Survey_Time'].min()
            st.metric("Fastest", f"{int(min_time // 60)}m {int(min_time % 60)}s")
        
        with col4:
            max_time = df['Total_Survey_Time'].max()
            st.metric("Slowest", f"{int(max_time // 60)}m {int(max_time % 60)}s")
        
        # Distribution of completion times
        st.markdown("### 📈 Completion Time Distribution")
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogram
            fig_hist = px.histogram(
                df,
                x='Total_Survey_Time',
                nbins=20,
                title="Distribution of Total Survey Time",
                labels={'Total_Survey_Time': 'Time (seconds)', 'count': 'Number of Responses'},
                color_discrete_sequence=['#4CAF50']
            )
            fig_hist.update_layout(showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Box plot
            fig_box = px.box(
                df,
                y='Total_Survey_Time',
                title="Survey Time Box Plot",
                labels={'Total_Survey_Time': 'Time (seconds)'},
                color_discrete_sequence=['#2196F3']
            )
            st.plotly_chart(fig_box, use_container_width=True)
        
        # Question-by-question time analysis
        st.markdown("### 🔍 Time Per Question")
        
        question_time_cols = [f'Q{i}_Time' for i in range(1, 13)]
        
        # Check if individual question time columns exist
        if all(col in df.columns for col in question_time_cols):
            # Calculate average time per question
            avg_times = []
            for q_col in question_time_cols:
                avg_times.append({
                    'Question': q_col.replace('_Time', ''),
                    'Average Time (seconds)': df[q_col].mean()
                })
            
            time_df = pd.DataFrame(avg_times)
            
            # Bar chart of average time per question
            fig_question_time = px.bar(
                time_df,
                x='Question',
                y='Average Time (seconds)',
                title="Average Time Spent on Each Question",
                color='Average Time (seconds)',
                color_continuous_scale='Teal',
                labels={'Average Time (seconds)': 'Avg Time (sec)'}
            )
            st.plotly_chart(fig_question_time, use_container_width=True)
            
            # Show which questions take longest
            time_df_sorted = time_df.sort_values('Average Time (seconds)', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**⏰ Longest Questions:**")
                for idx, row in time_df_sorted.head(3).iterrows():
                    st.write(f"{row['Question']}: {row['Average Time (seconds)']:.1f}s")
            
            with col2:
                st.markdown("**⚡ Fastest Questions:**")
                for idx, row in time_df_sorted.tail(3).iterrows():
                    st.write(f"{row['Question']}: {row['Average Time (seconds)']:.1f}s")
            
            # Time by MBTI type
            st.markdown("### 🐟 Completion Time by Fish Type")
            
            time_by_type = df.groupby('MBTI_Type')['Total_Survey_Time'].agg(['mean', 'count']).reset_index()
            time_by_type = time_by_type[time_by_type['count'] >= 2]  # Only show types with 2+ responses
            time_by_type = time_by_type.sort_values('mean', ascending=False)
            
            if len(time_by_type) > 0:
                fig_type_time = px.bar(
                    time_by_type,
                    x='MBTI_Type',
                    y='mean',
                    title="Average Completion Time by Personality Type",
                    labels={'mean': 'Average Time (seconds)', 'MBTI_Type': 'Fish Type'},
                    color='mean',
                    color_continuous_scale='Sunset'
                )
                st.plotly_chart(fig_type_time, use_container_width=True)
    else:
        st.info("⏱️ Time tracking data not available for this dataset.")
    
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
        ["🐟 Take Quiz", "📊 View Analytics"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "Dive into the world of local fish and discover which species matches "
        "your personality! Through 12 carefully designed questions, you'll explore "
        "your unique traits and find your fish counterpart. Share your results and "
        "view analytics to see how you compare with others in the sea! 🐟🌊"
    )
    
    # Page routing
    if page == "🐟 Take Quiz":
        survey_page()
    else:
        analytics_page()

if __name__ == "__main__":
    main()
