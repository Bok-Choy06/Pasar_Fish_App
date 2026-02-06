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

def get_image_base64(image_path):
    """Convert image to base64 for HTML display"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Set page config
st.set_page_config(
    page_title="Which Local Fish Are You?", 
    page_icon="🐟", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Force content to fit viewport */
    .main .block-container {
        max-height: 100vh;
        overflow-y: auto;
        padding: 1vh 2vw;
    }
    
    /* Scale everything to viewport */
    .main {
        padding: 1vh 2vw;
        max-width: 100vw;
    }
    
    /* Question container fits screen */
    .question-container {
        background-color: #f8f9fa;
        padding: 2vh 2vw;
        border-radius: 10px;
        margin: 1vh 0;
        max-height: 80vh;
        overflow: visible;
    }
    
    /* Images scale to screen */
    img {
        max-width: 100vw !important;
        max-height: 40vh !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        margin: 1vh auto !important;
        display: block !important;
    }

    /* Results page fish image - larger */
    .result-fish-image {
        max-width: 90vw !important;
        max-height: 70vh !important;  /* Much larger for results */
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        margin: 2vh auto !important;
        display: block !important;
    }
    
    /* Responsive text sizing */
    h1 {
        font-size: clamp(1.5rem, 4vw, 2.5rem) !important;
    }
    
    h3 {
        font-size: clamp(1rem, 3vw, 1.5rem) !important;
    }
    
    h4 {
        font-size: clamp(0.9rem, 2.5vw, 1.2rem) !important;
    }
    
    p, .stMarkdown {
        font-size: clamp(0.85rem, 2vw, 1rem) !important;
    }
    
    /* Button sizing */
    .stButton>button {
        font-size: clamp(0.9rem, 2.5vw, 1.1rem) !important;
        padding: 1vh 2vw !important;
    }
    
    /* Radio buttons and inputs */
    .stRadio, .stSelectbox {
        font-size: clamp(0.85rem, 2vw, 1rem) !important;
    }
    
    /* Reduce spacing between elements */
    .stMarkdown {
        margin-bottom: 0.5vh !important;
    }
    
    /* Progress bar */
    .stProgress {
        height: 1vh !important;
    }
    
    /* Responsive breakpoints */
    @media (max-height: 800px) {
        /* Smaller screens - compress more */
        .question-container {
            padding: 1.5vh 2vw;
        }
        img {
            max-height: 30vh !important;
        }
    }
    
    @media (max-height: 600px) {
        /* Very small screens - ultra compact */
        .question-container {
            padding: 1vh 1.5vw;
        }
        img {
            max-height: 25vh !important;
        }
        h1 {
            font-size: 1.3rem !important;
        }
    }
    
    @media (min-height: 1000px) {
        /* Large screens - more breathing room */
        img {
            max-height: 50vh !important;
        }
    }

    /* Force navigation buttons side-by-side on mobile */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 50% !important;
            flex: 1 1 50% !important;
            min-width: 0 !important;
        }
        
        /* Specifically for 3-column layouts (Previous, empty, Next) */
        div[data-testid="column"]:nth-child(2) {
            width: 0% !important;
            flex: 0 0 0% !important;
            padding: 0 !important;
        }
    }

    /* Aggressive space removal */
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Remove all top margins and padding */
    h1, h2, h3 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Tighten up the title specifically */
    .main .block-container > div:first-child {
        padding-top: 0 !important;
    }
    
    /* Remove Streamlit's default top spacing */
    .stApp > header {
        height: 0rem;
    }
    
    /* Compact everything at the top */
    section[data-testid="stAppViewContainer"] > div:first-child {
        padding-top: 0 !important;
    }
    
    /* Remove extra space above progress bar */
    .stProgress {
        margin-top: 0.25rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Tighten caption spacing */
    .stCaption {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Remove space above horizontal rules */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# JavaScript to detect and adjust to screen size
st.markdown("""
    <script>
    // Detect screen size and adjust zoom
    function adjustToScreen() {
        const screenHeight = window.innerHeight;
        const screenWidth = window.innerWidth;
        
        // Calculate optimal zoom level
        let zoomLevel = 1;
        
        if (screenHeight < 700) {
            zoomLevel = 0.85;  // Small screens - zoom out
        } else if (screenHeight < 900) {
            zoomLevel = 0.95;  // Medium screens - slight zoom out
        } else if (screenHeight > 1200) {
            zoomLevel = 1.1;   // Large screens - zoom in slightly
        }
        
        // Apply zoom
        document.body.style.zoom = zoomLevel;
        
        // Log for debugging
        console.log('Screen: ' + screenWidth + 'x' + screenHeight + ', Zoom: ' + zoomLevel);
    }
    
    // Run on load and resize
    window.addEventListener('load', adjustToScreen);
    window.addEventListener('resize', adjustToScreen);
    </script>
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
        <style>
        /* Share buttons - responsive layout */
        .share-container {
            background-color: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 2rem auto;
            max-width: 900px;
        }
        
        .share-icons {
            display: flex;
            justify-content: space-around;
            align-items: center;
            flex-wrap: wrap;
            gap: 2rem;
            padding: 1rem;
        }
        
        /* Mobile: single row, smaller icons, tighter spacing */
        @media (max-width: 768px) {
            .share-icons {
                flex-wrap: nowrap !important;
                gap: 0.5rem !important;
                padding: 0.5rem !important;
                overflow-x: auto;
                justify-content: space-between;
            }
            
            .share-icons i {
                font-size: 36px !important;
            }
            
            .share-container {
                padding: 1rem !important;
            }
        }
        </style>
        
        <div class="share-container">
            <h3 style="text-align: center; color: #333; margin-bottom: 2rem;">📢 Share Your Results!</h3>
            <div class="share-icons">
                <div style="text-align: center;">
                    <a href="https://www.instagram.com/" target="_blank">
                        <i class="fab fa-instagram" style="font-size: 48px; color: #E4405F;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + x_url + """ target="_blank">
                        <i class="fab fa-x-twitter" style="font-size: 48px; color: #000000;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + linkedin_url + """ target="_blank">
                        <i class="fab fa-linkedin" style="font-size: 48px; color: #0077B5;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + whatsapp_url + """ target="_blank">
                        <i class="fab fa-whatsapp" style="font-size: 48px; color: #25D366;"></i>
                    </a>
                </div>
                <div style="text-align: center;">
                    <a href=""" + telegram_url + """ target="_blank">
                        <i class="fab fa-telegram" style="font-size: 48px; color: #0088cc;"></i>
                    </a>
                </div>
            </div>
            <div style="text-align: center; margin-top: 1rem; color: #666;">
                💡 Click on the icons to share!
            </div>
        </div>
    """, unsafe_allow_html=True)
    
def show_follow_section():
    """Display Follow Pasar Fish section - reusable across all pages"""
    st.markdown("""
        <div style="background-color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 2rem auto; max-width: 900px;">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h3 style="color: #333; margin-bottom: 0.5rem;">🌐 Follow Pasar Fish!</h3>
                <p style="color: #666;">Stay connected with us for more fishy adventures:</p>
            </div>
            <div style="display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 2rem;">
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://pasarfish.com" target="_blank" style="text-decoration: none; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                        <i class="fas fa-globe" style="font-size: 48px; color: #4CAF50;"></i>
                        <span style="font-size: 14px; color: #4A90E2; font-weight: bold;">Pasarfish.com</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://instagram.com/pasarfishsg" target="_blank" style="text-decoration: none; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                        <i class="fab fa-instagram" style="font-size: 48px; color: #E4405F;"></i>
                        <span style="font-size: 14px; color: #4A90E2; font-weight: bold;">@Pasarfishsg</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://linkedin.com/company/pasarfish" target="_blank" style="text-decoration: none; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                        <i class="fab fa-linkedin" style="font-size: 48px; color: #0077B5;"></i>
                        <span style="font-size: 14px; color: #4A90E2; font-weight: bold;">@Pasarfish</span>
                    </a>
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <a href="https://www.facebook.com/p/Pasarfishsg-61568193013803/" target="_blank" style="text-decoration: none; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                        <i class="fab fa-facebook" style="font-size: 48px; color: #1877F2;"></i>
                        <span style="font-size: 14px; color: #4A90E2; font-weight: bold;">@Pasarfishsg</span>
                    </a>
                </div>
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
    
    # Skip progress bar on demographics page (step 0)
    if current == 0:
        return
    
    progress = current / total_steps
    
    st.progress(progress)
    if current <= 12:
        st.caption(f"Question {current} of 12")
    else:
        st.caption("✅ Complete!")

def demographics_page():
    """Show demographics collection page"""
    
    # Center-aligned title
    st.markdown("""
        <h1 style="text-align: center;">🐟 Which Local Fish Are You? </h1>
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
    
    # Track page start time (only set once per page load)
    if 'demographics_start_time' not in st.session_state:
        st.session_state.demographics_start_time = datetime.now()
    
    st.markdown("---")
    st.markdown("### 🌎 Demographics")
    
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
    
    # PDPA Consent Checkbox - REQUIRED
    st.markdown("---")
    st.markdown("### 📋 Data Privacy Consent")
    
    pdpa_consent = st.checkbox(
        "I consent to the collection, use, and disclosure of my personal data in accordance with Singapore's Personal Data Protection Act (PDPA) for the purposes of this survey and research. *",
        key="pdpa_consent"
    )
    
    st.caption("By checking this box, you agree that your responses may be stored and analyzed anonymously for research purposes.")
    
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
            if not pdpa_consent:
                st.error("❌ Please provide consent to proceed with the survey")
                return
            
            # Calculate time spent on demographics
            demographics_duration = (datetime.now() - st.session_state.demographics_start_time).total_seconds()
            
            # Save demographics (including consent)
            st.session_state.demographics = {
                'age': age,
                'gender': gender,
                'country': country if country else "Not specified",
                'occupation': occupation,
                'referral_source': referral_source,
                'pdpa_consent': 'Yes',  # Only saved if they checked it
                'demographics_time': round(demographics_duration, 2)
            }
            
            # Set start time for first question
            st.session_state.question_start_times['Q1'] = datetime.now()
            st.session_state.current_step = 1
            st.rerun()
            
    # Add follow section at bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
    show_follow_section()
    
def question_page(question_num):
    """Show individual question page"""
    q_id = f'Q{question_num}'
    q_data = questions[q_id]
    
    # Set start time for this question if not already set
    if q_id not in st.session_state.question_start_times:
        st.session_state.question_start_times[q_id] = datetime.now()
    
    # Compact title
    st.markdown(f'<h2 style="text-align: center; margin: 0.5rem 0;font-weight: 800;">🐟 Which Local Fish Are You?</h2>', unsafe_allow_html=True)
    
    show_progress()
    
    st.markdown("---")
    
    # COMPACT question container with viewport constraints
    st.markdown(f'<div style="max-height: 70vh; overflow: visible;">', unsafe_allow_html=True)
    
    # Question text - more compact
    st.markdown(f"### {q_data['text']}")
    
    # Image - constrained height
    if q_data['image']:
        if q_data['image'].startswith('http'):
            st.markdown(f'<img src="{q_data["image"]}" style="max-width: 100%; max-height: 30vh; display: block; margin: 0.5rem auto; border-radius: 10px;" />', unsafe_allow_html=True)
        else:
            if os.path.exists(q_data['image']):
                # Use columns to center and constrain
                col1, col2, col3 = st.columns([1, 3, 1])
                with col2:
                    st.image(q_data['image'], use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Answer options - compact
    st.markdown("### Choose one:")
    
    current_answer = st.session_state.answers.get(q_id)
    
    answer = st.radio(
        "Select your answer:",
        options=list(q_data['options'].keys()),
        format_func=lambda x: q_data['options'][x],
        index=list(q_data['options'].keys()).index(current_answer) if current_answer else 0,
        key=f"radio_{q_id}",
        label_visibility="collapsed"
    )
    
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
                
    # Add follow section at bottom of every question page
    st.markdown("<br>", unsafe_allow_html=True)
    show_follow_section()
    
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
    
    st.markdown("<h2 style='text-align: center;'>🎉 Your Fish!</h2>", unsafe_allow_html=True)

    # Display fish image instead of MBTI type text
    fish_image_path = fish_images.get(mbti_type)

    if fish_image_path and os.path.exists(fish_image_path):
        # Display the fish image at full width
        st.markdown(f'<img src="data:image/png;base64,{get_image_base64(fish_image_path)}" class="result-fish-image" />', unsafe_allow_html=True)
    else:
        # Fallback if image doesn't exist
        st.markdown(f"""
        <div class="result-box">
            <h1 style="color: #4CAF50; margin-bottom: 0.5rem;">{mbti_type}</h1>
            <h3 style="color: #555; margin-top: 0;">{description}</h3>
            <p style="color: #888;">Fish image not found. Please upload: {fish_image_path}</p>
        </div>
        """, unsafe_allow_html=True)

    # Retake button - smaller and centered
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
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
    
    # Share buttons
    create_share_buttons(mbti_type)
    
    st.markdown("---")

    # Follow section at bottom
    st.markdown("<br>", unsafe_allow_html=True)
    show_follow_section()
    
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

    # Map MBTI types to fish names - handle different possible column names
    if 'MBTI_Type' in df.columns:
        df['Fish_Name'] = df['MBTI_Type'].map(fish_names)
    elif 'MBTI Type' in df.columns:
        df['Fish_Name'] = df['MBTI Type'].map(fish_names)
    elif 'mbti_type' in df.columns:
        df['Fish_Name'] = df['mbti_type'].map(fish_names)
    else:
        st.error("⚠️ MBTI_Type column not found in data. Please check your Google Sheets column names.")
        st.write("Available columns:", df.columns.tolist())
        return
    
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
        most_common_mbti = df['MBTI_Type'].mode()[0] if len(df) > 0 else "N/A"
        most_common_fish = fish_names.get(most_common_mbti, most_common_mbti)
        st.metric("Most Common Fish", most_common_fish)
    
    with col4:
        today_responses = len(df[pd.to_datetime(df['Timestamp']).dt.date == datetime.now().date()])
        st.metric("Today's Responses", today_responses)
    
    st.markdown("---")
    
    # MBTI Type Distribution
    st.markdown("## 🎯 Fish Type Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart with fish names
        type_counts = df['Fish_Name'].value_counts()
        fig_pie = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Fish Types Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart with fish names
        fig_bar = px.bar(
            x=type_counts.index,
            y=type_counts.values,
            title="Fish Types Count",
            labels={'x': 'Fish Type', 'y': 'Count'},
            color=type_counts.values,
            color_continuous_scale='Viridis'
        )
        fig_bar.update_xaxes(tickangle=-45)
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
            
            # Time by Fish Type
            st.markdown("### 🐟 Completion Time by Fish Type")
            
            time_by_type = df.groupby('Fish_Name')['Total_Survey_Time'].agg(['mean', 'count']).reset_index()
            time_by_type = time_by_type[time_by_type['count'] >= 2]  # Only show types with 2+ responses
            time_by_type = time_by_type.sort_values('mean', ascending=False)
            
            if len(time_by_type) > 0:
                fig_type_time = px.bar(
                    time_by_type,
                    x='Fish_Name',
                    y='mean',
                    title="Average Completion Time by Fish Type",
                    labels={'mean': 'Average Time (seconds)', 'Fish_Name': 'Fish Type'},
                    color='mean',
                    color_continuous_scale='Sunset'
                )
                fig_type_time.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_type_time, use_container_width=True)
    else:
        st.info("⏱️ Time tracking data not available for this dataset.")

    st.markdown("---")
    
    # 1. DEMOGRAPHICS VS FISH TYPE ANALYSIS
    st.markdown("## 🔬 Demographics & Fish Type Correlations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Age vs Fish Type
        st.markdown("### Age Distribution by Fish Type")
        age_fish_crosstab = pd.crosstab(df['Age'], df['Fish_Name'])
        fig_age_fish = px.imshow(
            age_fish_crosstab,
            labels=dict(x="Fish Type", y="Age Range", color="Count"),
            title="Age vs Fish Type Heatmap",
            color_continuous_scale='Blues',
            aspect='auto'
        )
        fig_age_fish.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_age_fish, use_container_width=True)
    
    with col2:
        # Gender vs Fish Type
        st.markdown("### Gender Distribution by Fish Type")
        gender_fish_crosstab = pd.crosstab(df['Gender'], df['Fish_Name'])
        fig_gender_fish = px.imshow(
            gender_fish_crosstab,
            labels=dict(x="Fish Type", y="Gender", color="Count"),
            title="Gender vs Fish Type Heatmap",
            color_continuous_scale='Purples',
            aspect='auto'
        )
        fig_gender_fish.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_gender_fish, use_container_width=True)
    
    # Occupation vs Fish Type
    st.markdown("### Occupation Distribution by Fish Type")
    occupation_fish_crosstab = pd.crosstab(df['Occupation'], df['Fish_Name'])
    fig_occ_fish = px.imshow(
        occupation_fish_crosstab,
        labels=dict(x="Fish Type", y="Occupation", color="Count"),
        title="Occupation vs Fish Type Heatmap",
        color_continuous_scale='Greens',
        aspect='auto'
    )
    fig_occ_fish.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_occ_fish, use_container_width=True)
    
    st.markdown("---")
    
    # 2. GEOGRAPHIC ANALYSIS
    st.markdown("## 🌍 Geographic Distribution")
    
    if 'Country' in df.columns and df['Country'].notna().sum() > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Top countries
            country_counts = df['Country'].value_counts().head(10)
            fig_countries = px.bar(
                x=country_counts.values,
                y=country_counts.index,
                orientation='h',
                title="Top 10 Countries",
                labels={'x': 'Number of Responses', 'y': 'Country'},
                color=country_counts.values,
                color_continuous_scale='Teal'
            )
            st.plotly_chart(fig_countries, use_container_width=True)
        
        with col2:
            # Fish type by top countries
            top_countries = df['Country'].value_counts().head(5).index
            df_top_countries = df[df['Country'].isin(top_countries)]
            
            country_fish = pd.crosstab(df_top_countries['Country'], df_top_countries['Fish_Name'])
            fig_country_fish = px.imshow(
                country_fish,
                labels=dict(x="Fish Type", y="Country", color="Count"),
                title="Fish Type Distribution by Top Countries",
                color_continuous_scale='RdYlBu',
                aspect='auto'
            )
            fig_country_fish.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_country_fish, use_container_width=True)
    
    st.markdown("---")
    
    # 3. REFERRAL SOURCE EFFECTIVENESS
    st.markdown("## 📣 Referral Source Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Completion time by referral source
        st.markdown("### Avg Completion Time by Source")
        if 'Total_Survey_Time' in df.columns:
            time_by_source = df.groupby('Referral_Source')['Total_Survey_Time'].mean().sort_values(ascending=False)
            fig_source_time = px.bar(
                x=time_by_source.values,
                y=time_by_source.index,
                orientation='h',
                title="Average Time by Referral Source",
                labels={'x': 'Avg Time (seconds)', 'y': 'Source'},
                color=time_by_source.values,
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig_source_time, use_container_width=True)
    
    with col2:
        # Fish type diversity by referral source
        st.markdown("### Fish Type Diversity by Source")
        source_diversity = df.groupby('Referral_Source')['Fish_Name'].nunique().sort_values(ascending=False)
        fig_source_div = px.bar(
            x=source_diversity.values,
            y=source_diversity.index,
            orientation='h',
            title="Unique Fish Types per Source",
            labels={'x': 'Number of Unique Fish Types', 'y': 'Source'},
            color=source_diversity.values,
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_source_div, use_container_width=True)
    
    st.markdown("---")
    
    # 4. RESPONSE PATTERNS OVER TIME
    st.markdown("## 📅 Temporal Patterns")
    
    if 'Timestamp' in df.columns:
        df['Hour'] = pd.to_datetime(df['Timestamp']).dt.hour
        df['DayOfWeek'] = pd.to_datetime(df['Timestamp']).dt.day_name()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Hourly distribution
            hourly_counts = df['Hour'].value_counts().sort_index()
            fig_hourly = px.line(
                x=hourly_counts.index,
                y=hourly_counts.values,
                title="Response Distribution by Hour of Day",
                labels={'x': 'Hour (24h)', 'y': 'Number of Responses'},
                markers=True
            )
            st.plotly_chart(fig_hourly, use_container_width=True)
        
        with col2:
            # Day of week distribution
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts = df['DayOfWeek'].value_counts().reindex(day_order, fill_value=0)
            fig_dow = px.bar(
                x=day_counts.index,
                y=day_counts.values,
                title="Response Distribution by Day of Week",
                labels={'x': 'Day', 'y': 'Number of Responses'},
                color=day_counts.values,
                color_continuous_scale='Plasma'
            )
            st.plotly_chart(fig_dow, use_container_width=True)
    
    st.markdown("---")
    
    # 5. QUESTION DIFFICULTY ANALYSIS
    st.markdown("## 🎯 Question Analysis")
    
    question_cols = [f'Q{i}' for i in range(1, 13)]
    
    # Most common answers per question
    st.markdown("### Most Popular Answers by Question")
    
    popular_answers = []
    for q in question_cols:
        if q in df.columns:
            mode_val = df[q].mode()[0] if len(df[q].mode()) > 0 else 'N/A'
            mode_pct = (df[q] == mode_val).sum() / len(df) * 100
            popular_answers.append({
                'Question': q,
                'Most Common Answer': mode_val,
                'Percentage': f'{mode_pct:.1f}%',
                'Count': (df[q] == mode_val).sum()
            })
    
    popular_df = pd.DataFrame(popular_answers)
    
    fig_popular = px.bar(
        popular_df,
        x='Question',
        y='Count',
        title="Most Popular Answer Distribution by Question",
        labels={'Count': 'Number of People'},
        color='Count',
        color_continuous_scale='Sunset',
        hover_data=['Most Common Answer', 'Percentage']
    )
    st.plotly_chart(fig_popular, use_container_width=True)
    
    # Show table
    st.dataframe(popular_df, use_container_width=True)
    
    st.markdown("---")
    
    # 6. PERSONALITY DIMENSIONS CORRELATION
    st.markdown("## 🧬 Dimension Correlations")
    
    # Create dimension combinations analysis
    if all(col in df.columns for col in ['E_I', 'S_N', 'T_F', 'J_P']):
        st.markdown("### Combined Dimension Patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # E/I vs S/N
            ei_sn = pd.crosstab(df['E_I'], df['S_N'])
            fig_ei_sn = px.imshow(
                ei_sn,
                labels=dict(x="S/N", y="E/I", color="Count"),
                title="E/I vs S/N Distribution",
                color_continuous_scale='RdBu',
                text_auto=True
            )
            st.plotly_chart(fig_ei_sn, use_container_width=True)
        
        with col2:
            # T/F vs J/P
            tf_jp = pd.crosstab(df['T_F'], df['J_P'])
            fig_tf_jp = px.imshow(
                tf_jp,
                labels=dict(x="J/P", y="T/F", color="Count"),
                title="T/F vs J/P Distribution",
                color_continuous_scale='YlGnBu',
                text_auto=True
            )
            st.plotly_chart(fig_tf_jp, use_container_width=True)
    
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

    # Follow section at bottom
    st.markdown("<br>", unsafe_allow_html=True)
    show_follow_section()

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
