import streamlit as st
import google.generativeai as genai
import json

# --- Page Configuration ---
st.set_page_config(page_title="ഉഴവൻ உணவு", layout="centered")

# --- Authenticate with Google AI ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except KeyError:
    st.error("Google API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Functions ---
def load_data():
    """Loads market and logistics data from the JSON file."""
    with open('market_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_ai_recommendation(query, market_data):
    """Generates a recommendation using the Google Gemini API."""
    market_data_str = json.dumps(market_data, indent=2)
    
    # The master prompt that instructs the AI
    prompt = f"""
    You are 'Uzhavan Thozhan' (Farmer's Friend), an expert AI assistant for farmers in Tamil Nadu. 
    Your goal is to provide clear, actionable advice in simple Tamil to help them get the best price for their produce. 
    Be encouraging and respectful.

    Here is the current market and logistics data:
    <data>
    {market_data_str}
    </data>

    Here is the farmer's query:
    <query>
    {query}
    </query>

    Based on all this information, perform the following steps:
    1. Analyze the farmer's product and quantity from the query.
    2. For each market, calculate the total potential revenue (Price per kg * quantity).
    3. For markets outside the farmer's home city, calculate the total logistics cost (Cost per kg * quantity) and subtract it to find the net profit.
    4. Compare the net profit for all options.
    5. Provide a final, clear recommendation in simple Tamil. Start with the single best option. 
    6. Show your calculations in a simple table.
    7. Finally, list the pros and cons of the other options.
    """
    
    # Initialize the Gemini model with a valid name from your list
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text

# --- Streamlit UI ---
st.title("🌾 உழவன் உணவு - Uzhavan Unavu")
st.subheader("உங்கள் விளைபொருளுக்கு சிறந்த விலை இங்கே பெறுங்கள்")

# Load market data
market_data = load_data()

# User Input
user_query = st.text_area(
    "உங்கள் கேள்வியை இங்கே உள்ளிடவும் (Enter your query here):",
    "எனக்கு மதுரையில் 50 கிலோ மல்லிகைப்பூ உள்ளது. நாளைக்கு எங்கே சிறந்த விலை கிடைக்கும்?"
)

if st.button("ஆலோசனை பெறுக (Get Advice)", type="primary"):
    if not user_query:
        st.warning("தயவுசெய்து உங்கள் கேள்வியை உள்ளிடவும்.")
    else:
        with st.spinner("உங்களுக்காக சிறந்த சந்தையை தேடிக்கொண்டிருக்கிறோம்..."):
            recommendation = get_ai_recommendation(user_query, market_data)
            st.markdown(recommendation)