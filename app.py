import streamlit as st
import pandas as pd
import requests
import re
import matplotlib.pyplot as plt
import plotly.express as px
import speech_recognition as sr
import google.generativeai as genai
from datetime import datetime
from PIL import Image
import tempfile

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="AI Nutrition Assistant", layout="wide")

# -----------------------------
# API KEYS
# -----------------------------
NUTRITIONIX_APP_ID = "678ba4d0"
NUTRITIONIX_API_KEY = "435af285033df449cc239381ba042d15"
USDA_API_KEY = "kk1HZzbU1tGtDrms8uzqayUWP0UIRxVHh9YUqBkz"
genai.configure(api_key="AIzaSyAvnZbSgHPNorBX6MtSFMEMBDmL5y0G-yI")
model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

# -----------------------------
# STATE
# -----------------------------
if "calorie_log" not in st.session_state:
    st.session_state.calorie_log = pd.DataFrame(columns=["Date", "Meal", "Food", "Calories"])

# -----------------------------
# FUNCTIONS
# -----------------------------
def fetch_calories(food_item):
    url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
    headers = {
        "x-app-id": NUTRITIONIX_APP_ID,
        "x-app-key": NUTRITIONIX_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"query": food_item}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        if result.get("foods"):
            calories = result["foods"][0]["nf_calories"]
            return float(calories)
    return None

def log_meal(food_item, meal_type):
    calories = fetch_calories(food_item)
    if calories is None:
        return "⚠️ Unable to fetch calorie data."
    new_entry = pd.DataFrame([{
        "Date": datetime.now().date(),
        "Meal": meal_type,
        "Food": food_item,
        "Calories": calories
    }])
    st.session_state.calorie_log = pd.concat([st.session_state.calorie_log, new_entry], ignore_index=True)
    return f"✅ Logged: {food_item} ({meal_type}) = {calories} kcal."

def get_summary():
    if st.session_state.calorie_log.empty:
        return "No meals logged yet."
    df = st.session_state.calorie_log
    summary = df.groupby("Meal")["Calories"].sum()
    total = summary.sum()
    text = "\n".join([f"**{meal}**: {cal} kcal" for meal, cal in summary.items()])
    return f"#### Summary\n{text}\n\n**Total Calories:** {total} kcal"

def plot_bar_chart():
    if st.session_state.calorie_log.empty:
        return
    chart_data = st.session_state.calorie_log.groupby("Meal")["Calories"].sum().reset_index()
    fig = px.bar(chart_data, x="Meal", y="Calories", title="Calories per Meal", color="Meal", text="Calories")
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

def transcribe_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening... Speak now")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except:
        return "❌ Could not recognize speech."

def suggest_meal(remaining_calories):
    try:
        cal = int(remaining_calories)
        prompt = f"Suggest an Indian meal under {cal} calories with high protein and fiber."
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ Enter a valid calorie number."

def generate_meal_plan(age, gender, goal, allergies, preferences, medical, cultural, lifestyle):
    prompt = f"""Create a personalized Indian meal plan with three meals for:\n
**Age**: {age}\n**Gender**: {gender}\n**Goal**: {goal}\n**Allergies**: {allergies}\n**Preferences**: {preferences}\n**Medical Conditions**: {medical}\n**Cultural Background**: {cultural}\n**Lifestyle**: {lifestyle}\n
Format using Breakfast, Lunch, Dinner."""
    response = model.generate_content(prompt)
    return response.text

def chat_with_coach(query):
    prompt = f"As a certified nutritionist, answer this: {query}"
    response = model.generate_content(prompt)
    return response.text

def analyze_food_image(image):
    image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    image.save(image_path.name)
    with open(image_path.name, "rb") as f:
        image_bytes = f.read()
    response = model.generate_content(["Estimate nutrients and identify food from this image:", image_bytes])
    return response.text

# -----------------------------
# UI LAYOUT
# -----------------------------
st.title("🥗 AI Nutrition Assistant")
st.markdown("### Powered by Gemini, Nutritionix & Streamlit")

with st.sidebar:
    st.header("📝 Log a Meal")
    food = st.text_input("Food Item")
    meal = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
    if st.button("Log Meal"):
        result = log_meal(food, meal)
        st.success(result)

    st.divider()

    st.header("🎤 Voice Logging")
    if st.button("Record Voice Meal"):
        transcribed = transcribe_audio()
        st.info(f"Transcribed: {transcribed}")
        if transcribed:
            result = log_meal(transcribed, "Lunch")
            st.success(result)

    st.divider()

    st.header("🖼️ Upload Food Image")
    uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    if uploaded_image and st.button("Analyze Image"):
        img = Image.open(uploaded_image)
        st.image(img, caption="Uploaded Image", use_column_width=True)
        response = analyze_food_image(img)
        st.session_state["image_analysis"] = response

    st.divider()

    st.header("🧠 Ask Nutrition Coach")
    if st.button("🎤 Ask with Voice"):
        coach_voice = transcribe_audio()
        st.session_state.coach_query = coach_voice

    coach_query = st.text_input("Your Question", key="coach_query")
    if st.button("Ask"):
        answer = chat_with_coach(coach_query)
        st.session_state.coach_response = answer

    st.divider()

    st.header("💡 Suggest Meal")
    remaining_cal = st.text_input("Remaining Calories")
    if st.button("Suggest"):
        suggestion = suggest_meal(remaining_cal)
        st.session_state["suggestion"] = suggestion

    st.divider()

    st.header("📋 Generate Meal Plan")
    age = st.number_input("Age", min_value=1, value=30)
    gender = st.selectbox("Gender", ["Male", "Female"])
    goal = st.selectbox("Goal", ["Muscle Gain", "Weight Loss", "Maintenance"])
    allergies = st.text_input("Allergies")
    preferences = st.text_input("Preferences")
    medical = st.text_input("Medical Conditions")
    cultural = st.text_input("Cultural Background")
    lifestyle = st.selectbox("Lifestyle", ["Sedentary", "Moderately Active", "Very Active"])
    if st.button("Generate Plan"):
        plan = generate_meal_plan(age, gender, goal, allergies, preferences, medical, cultural, lifestyle)
        st.session_state["plan"] = plan

# -----------------------------
# MAIN OUTPUT SECTION
# -----------------------------
st.markdown("### 📦 Output Panel")

with st.container():
    st.markdown("#### 🧾 Calorie Summary")
    st.markdown(get_summary())
    plot_bar_chart()

    if "image_analysis" in st.session_state:
        st.markdown("#### 📷 Image Analysis")
        st.info(st.session_state.image_analysis)

    if "suggestion" in st.session_state:
        st.markdown("#### 🍱 Suggested Meal")
        st.info(st.session_state.suggestion)

    if "coach_response" in st.session_state:
        st.markdown("#### 🧑‍⚕️ Nutrition Coach Says")
        st.success(st.session_state.coach_response)

    if "plan" in st.session_state:
        st.markdown("#### 🥗 Personalized Meal Plan")
        st.markdown(st.session_state.plan)
