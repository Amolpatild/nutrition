#Import all the necessay pacakges
import streamlit as st
import pandas as pd
import requests
import re
import matplotlib.pyplot as plt
import speech_recognition as sr
import google.generativeai as genai
from datetime import datetime
import plotly.express as px
from PIL import Image

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="The Smartest AI Nutrition Assistant", layout="wide")

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
if "image_analysis_result" not in st.session_state:
    st.session_state.image_analysis_result = ""
if "coach_response" not in st.session_state:
    st.session_state.coach_response = ""

# -----------------------------
# fetch_calories FUNCTION-Let's fetch the real time calories from NUTRITIONIX_APP
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
# -----------------------------
# log_meal FUNCTION-Let's fetch the real time calories from NUTRITIONIX_APP and store it in the dataframe
# -----------------------------
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

# -----------------------------
# get_summary FUNCTION-Let's summrize calories and calculate the total calories
# -----------------------------
def get_summary():
    if st.session_state.calorie_log.empty:
        return "No meals logged yet."
    df = st.session_state.calorie_log
    summary = df.groupby("Meal")["Calories"].sum()
    total = summary.sum()
    text = "\n".join([f"{meal}: {cal:.2f} kcal" for meal, cal in summary.items()])
    return f"### Summary\n{text}\n\n**Total Calories:** {total:.2f} kcal"

# -----------------------------
# plot_bar_chart FUNCTION- To plot the bar graph for better visulization.
# -----------------------------
def plot_bar_chart():
    if st.session_state.calorie_log.empty:
        return
    chart_data = st.session_state.calorie_log.groupby("Meal")["Calories"].sum().reset_index()
    fig = px.bar(chart_data, x="Meal", y="Calories", color="Meal", title="Meal-wise Calorie Breakdown")
    st.plotly_chart(fig)

# -----------------------------
# transcribe_audio FUNCTION- To recognize the voice
# -----------------------------
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

# -----------------------------
# suggest_meal FUNCTION- To suggest the remaining calories food.
# -----------------------------
def suggest_meal(remaining_calories):
    try:
        cal = int(remaining_calories)
        prompt = f"Suggest an Indian meal under {cal} calories with high protein and fiber."
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ Enter a valid calorie number."

# -----------------------------
# generate_meal_plan FUNCTION- To generate the persionalize food plan.
# -----------------------------
def generate_meal_plan(age, gender, goal, allergies, preferences, medical, cultural, lifestyle):
    prompt = f"""Create a personalized Indian meal plan with three meals for:
- Age: {age}
- Gender: {gender}
- Goal: {goal}
- Allergies: {allergies}
- Preferences: {preferences}
- Medical Conditions: {medical}
- Cultural Background: {cultural}
- Lifestyle: {lifestyle}
Format using Breakfast, Lunch, Dinner."""
    response = model.generate_content(prompt)
    return response.text.replace("**", "")  # Remove asterisks

# -----------------------------
# chat_with_coach FUNCTION- To discuss the any queey regarding the nutrition.
# -----------------------------
def chat_with_coach(query):
    prompt = f"As a certified nutritionist, answer this: {query}"
    response = model.generate_content(prompt)
    return response.text

# -----------------------------
# analyze_food_image FUNCTION- To anyze the ingredients nutrition informatin by uploading image.
# -----------------------------
def analyze_food_image(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        response = model.generate_content(["Estimate nutrients and identify food from this image:", image])
        return response.text
    except Exception as e:
        return f"Image analysis failed: {str(e)}"

# -----------------------------
# UI LAYOUT
# -----------------------------
st.title("🥗 The Smartest AI Nutrition Assistant ")
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
    if st.button("Record Voice"):
        transcribed = transcribe_audio()
        st.info(f"Transcribed: {transcribed}")
        if transcribed:
            result = log_meal(transcribed, "Lunch")
            st.success(result)

    st.divider()

    st.header("💡 Suggest Meal")
    remaining_cal = st.text_input("Remaining Calories")
    if st.button("Suggest"):
        suggestion = suggest_meal(remaining_cal)
        st.session_state["suggestion"] = suggestion

    st.divider()

    st.markdown("### 🧑‍⚕️ Ask Nutrition Coach")

    # Use a temporary variable for voice transcription
    if "transcribed_coach_question" not in st.session_state:
        st.session_state.transcribed_coach_question = ""

    # Layout for input
    col1, col2 = st.columns([3, 1])

    with col1:
        # Use the voice transcription as default text input
        coach_input = st.text_area("Type your question or use voice", value=st.session_state.transcribed_coach_question, key="coach_input",height=100)

    with col2:
        if st.button("🎤 Voice Input"):
            transcribed = transcribe_audio()
            if transcribed and "could not recognize" not in transcribed.lower():
                st.session_state.transcribed_coach_question = transcribed
                st.rerun()
            else:
                st.warning("Could not recognize speech.")

    # Ask button logic
    if st.button("Ask Coach"):
        query = coach_input.strip()
        if query:
            st.session_state["coach"] = chat_with_coach(query)
        else:
            st.warning("Please enter a question or use voice.")


    st.divider()

    st.header("📸 Image Analysis")
    uploaded_image = st.file_uploader("Upload Food Image", type=["jpg", "jpeg", "png"])
    if uploaded_image and st.button("Analyze Image"):
        with st.spinner("Analyzing image..."):
            result = analyze_food_image(uploaded_image)
            st.session_state["image_analysis_result"] = result

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

    if st.session_state.get("suggestion"):
        st.markdown("#### 🍱 Suggested Meal")
        st.info(st.session_state["suggestion"])

    if st.session_state.get("coach_response"):
        st.markdown("#### 🧑‍⚕️ Nutrition Coach Says")
        st.success(st.session_state["coach_response"])

    if st.session_state.get("image_analysis_result"):
        st.markdown("#### 🖼️ Image Analysis Result")
        st.success(st.session_state["image_analysis_result"])

    if "coach" in st.session_state and st.session_state.coach:
            st.markdown("#### 🧑‍⚕️ Nutrition Coach Says")
            st.success(st.session_state["coach"])

    if st.session_state.get("plan"):
        st.markdown("#### 🥗 Personalized Meal Plan")
        st.text_area("Generated Plan", st.session_state["plan"], height=300)


