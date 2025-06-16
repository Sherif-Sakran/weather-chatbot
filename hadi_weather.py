from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
import streamlit as st
import os
from dotenv import load_dotenv
import json
import datetime
import requests
import regex
import re
from dateutil import parser
import dateparser
from datetime import datetime

load_dotenv()
os.environ["LANGSMITH_TRACING"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGSMITH_API_KEY")

API_KEY = os.getenv("FREEWEATHER_API_KEY")  # store your key in .env

def get_lat_lon(city):
    url = f"https://nominatim.openstreetmap.org/search"
    params = {
        'q': city,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'AppName/1.0 (email@example.com)'
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    if data:
        print(f"Found coordinates for {city}: {data[0]['lat']}, {data[0]['lon']}")
        return float(data[0]['lat']), float(data[0]['lon'])
    return None

# def get_weather(lat, lon):
#     url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}"
#     response = requests.get(url)
#     if response.status_code == 200:
#         print("Weather data fetched successfully.")
#         return response.json()
#     print("Error fetching weather data:", response.status_code, response.text)
#     return response.text

def get_weather(lat, lon, date):
    print(f"Fetching weather for coordinates: {lat}, {lon} on date: {date}")
    if date.date() < datetime.today().date():
        url = f"http://api.weatherapi.com/v1/history.json?key={API_KEY}&q={lat},{lon}&dt={date}"
    else:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={lat},{lon}&unixdt={date.timestamp()}"

    # url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}&unixdt={date}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Weather data fetched successfully.")
        return response.json()
    print("Error fetching weather data:", response.status_code, response.text)
    return response.text

def extract_json_from_text(text):
    try:
        match = regex.search(r'\{(?:[^{}]|(?R))*\}', text)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
    return None

def extract_info_from_response(text):
    intent = None
    city = None
    date = None

    if isinstance(text, bytes):
        text = text.decode()
    text = str(text).strip()

    # Normalize None to null for valid JSON parsing
    text = text.replace("None", "null")

    # Remove markdown code blocks if present
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    parsed_data = None

    # Attempt 1: parse entire text as JSON
    try:
        parsed_data = json.loads(text)
    except json.JSONDecodeError:
        # Attempt 2: Extract substring from first { to last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            try:
                parsed_data = json.loads(candidate)
            except json.JSONDecodeError:
                parsed_data = None

    def get_field(source, key):
        if not isinstance(source, dict):
            return None
        for k, v in source.items():
            if k.lower() == key.lower():
                # Handle nested date dictionary
                if isinstance(v, dict) and key.lower() == "date":
                    month = v.get("month", "")
                    day = v.get("day", "")
                    date_str = f"{month} {day}".strip()
                    return date_str if date_str else None
                if v is None or (isinstance(v, str) and v.strip().lower() in ["none", "null"]):
                    return None
                return str(v).strip()
        return None

    if parsed_data:
        intent = get_field(parsed_data, "intent")
        city = get_field(parsed_data, "city")
        date = get_field(parsed_data, "date")

    # Fallback regex if fields missing
    if not intent:
        m = re.search(r'intent\s*[:=]\s*["\']?([\w\s]+)', text, re.IGNORECASE)
        if m:
            intent = m.group(1).strip()
    if not city:
        m = re.search(r'city\s*[:=]\s*["\']?([\w\s\-]+)', text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            city = None if val.lower() in ["none", "null"] else val
    if not date:
        m = re.search(r'date\s*[:=]\s*["\']?([A-Za-z0-9 ,\-]+)', text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            date = None if val.lower() in ["none", "null"] else val

    print(f"Intent: {intent}, City: {city}, Date: {date}")
    return intent, city, date


directory = '..\examples'
examples = ""

# counter = 1
# for filename in os.listdir(directory):
#     if filename.endswith('.txt'):
#         examples += f"Example {counter}:\n"
#         counter += 1
#         filepath = os.path.join(directory, filename)
#         with open(filepath, 'r', encoding='utf-8') as file:
#             examples += file.read()
# examples = examples.replace("{", "{{").replace("}", "}}")

get_weather_examples = """
Example 1:
USER: What does the weather on March 14th look like?
ASSISSTANT: 
- Intent: GetWeather
- Slots: {'date': ['March 14th'], 'city': ['']}}
ASSISSTANT: Which city should I check it for?
USER: Search in Mill Valley
ASSISSTANT:
- Intent: GetWeather
- Slots: {'city': ['Mill Valley'], 'date': ['March 14th']}

"""
get_weather_examples = get_weather_examples.replace("{", "{{").replace("}", "}}")

get_details_examples = """
Example 1:
USER: What's the weather like on Thursday next week?
ASSISSTANT: 
- Intent: GetWeather
- Slots: {'date': ['Thursday next week'], 'city': ['']}

ASSISSTANT: For what city?

USER: Look in Sebastopol.
ASSISSTANT: 
- Intent: GetWeather
- Slots: {'city': ['Sebastopol'], 'date': ['Thursday next week']}

ASSISSTANT (after calling the API): The average temperature should be X degrees Fahrenheit.

USER: Will it be windy? How humid?
ASSISSTANT: 
- Intent: GetDetails
- Slots: {'request': ['humidity', 'wind']}

"""
get_details_examples = get_details_examples.replace("{", "{{").replace("}", "}}")

# print(examples[:150])

## streamlit framework
st.set_page_config(page_title="Hadi Chatbot", page_icon="🌜")
# st.set_page_config(page_title="Hadi Chatbot", page_icon=":robot_face:", layout="wide")

# st.title('Hadi Chatbot')
st.markdown("<h1 style='text-align: center;'>Hadi Chatbot</h1>", unsafe_allow_html=True)
# input_text=st.text_input("Chat with me!", placeholder="Ask me about the weather...")

# ChatOllama
llm=ChatOllama(model="llama3.2")

output_parser=StrOutputParser()

# chain= prompt | llm | output_parser

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

if "weather_city_context" not in st.session_state:
    st.session_state.weather_city_context = {"city": None, "date": datetime.now()}

def k_to_c(k): return round(k - 273.15, 1)



# Ask for new input
input_text = st.chat_input("Ask me about the weather...")

if input_text:
    st.session_state.conversation_history.append(("user", input_text))
    
    full_prompt = [
        ("system","""You are an NLU module designed to understand the user's messages and classify their intent to one of the following: 
        1) Intent = GetWeather
        - Triggered when user asks any general **weather** questions. It does not have to mention the word 'weather'. As long as the user mentions a city, you should assume they want to know the weather. 
        - Rules:
            - Return `Intent`, `city`, and `date` in JSON format.
            - If the user does not provide a city, it is None.
            - If the user does not provide a date, it is None.
            - This is not about what you known about the weather. It is just about extracting the user's intent.
        - Example user messages: `What about [city]?` or `How is it gonna be in Aswan?` or `What is the weather in [city] on March 14th?` or `What does the weather look like?` or `What is the weather like in [city]?` or `What is the weather in Aswan on March 14th?` or `How is it gonna be in [city]?` or `Check the weather in [city]` or `What do you think the weather will be like in [city]?` or `What will the weather be like in [city]?` `Could you check the weather in [city]?` or `How is the weather gonna be like?`
         2) Intent = GetDetails
        - Triggered when user asks for weather specifics like humidity or wind.
        - Rules:
            - Return `Intent` in JSON format.
            - Do NOT answer the user's question. Only return the intent and request in JSON format.
            - Request can only be about humidity or wind.
            - Do NOT ask follow-up questions.
        - Example user messages: `What about the humidity?` or `How windy is it?` or `Any wind` or `Is it windy?`
        3) Intent = Other
        - Triggered when the user's message does not match any of the above intents. This includes any general questions or statements that do not pertain to weather.
         - Rules:
            - Return `Intent` in JSON format.
            - Do NOT answer the user's question. Only return the intent in JSON format.
            - Do NOT ask follow-up questions.""")
    ] + st.session_state.conversation_history[-6:]

    prompt = ChatPromptTemplate.from_messages(full_prompt)
    # for role, content in full_prompt:
    #     print(f"*{role.upper()}*: {content}\n")
    chain = prompt | llm | output_parser
    result = chain.invoke({})  # No extra vars needed if it's just conversation

    # escaped_result = result.replace("{", "{{").replace("}", "}}")
    # st.session_state.conversation_history.append(("assistant", escaped_result))


    print(f"\n\n\n\nMain Prompt: {prompt}")
    print(f'\n\nMain Prompt res: {result}')

    intent, city, date = extract_info_from_response(result)
    print(f"Extracted intent: {intent}, city: {city}, date: {date}")
    context_summary = ""
    if intent == "GetWeather":
        if city:
            if not date or date == "None" or date == "" or date == "null":
                date = datetime.now()
            if isinstance(date, str):
                date = dateparser.parse(date)
            print(f"Calling weather forecast API for city: {city}, date: {date}")
            lat, lon = get_lat_lon(city)
            weather_data = get_weather(lat, lon, date)
            print(f"API received data: {weather_data}")
            past_forecast = " (note that it is a weather in the past)" if date.date() < datetime.today().date() else ""

            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a weather assistant. Write the weather forecast in summary{past_forecast}. Here is the information: city: {city}, date: {date.strftime('%Y-%m-%d')}, max_temperature: {weather_data['forecast']['forecastday'][0]['day']['maxtemp_c']}°C, min_temperature: {weather_data['forecast']['forecastday'][0]['day']['mintemp_c']}°C, average_temperature: {weather_data['forecast']['forecastday'][0]['day']['avgtemp_c']}°C"""),
                ("user", f"Tell me about the weather for {city} on {date.strftime('%Y-%m-%d')}."),
                ("assistant", "The weather..."),
            ])
            chain = prompt | llm | output_parser
            # chain = prompt | llm
            result = chain.invoke({})
            print(f"\n\n\n\nSummary Prompt: {prompt}")
            print(f'\n\nSummary Prompt result: {result}')
            # result = f"""The weather in {city} is {weather_data['weather'][0]['description']}
            # with a temperature of {weather_data['main']['temp'] - 273.15:.1f}°C."""

            context_summary = f"""Today is {datetime.now().strftime('%Y-%m-%d')}) and these are the weather details obtained from the weatherapi.com API for {city} on {date}:
            max_temperature: {weather_data['forecast']['forecastday'][0]['day']['maxtemp_c']}°C, min_temperature: {weather_data['forecast']['forecastday'][0]['day']['mintemp_c']}°C, average_temperature: {weather_data['forecast']['forecastday'][0]['day']['avgtemp_c']}°C, maxwind_mph: {weather_data['forecast']['forecastday'][0]['day']['maxwind_mph']} mph, totalprecip_mm: {weather_data['forecast']['forecastday'][0]['day']['totalprecip_mm']} mm, avgvis_km: {weather_data['forecast']['forecastday'][0]['day']['avgvis_km']} km, avghumidity: {weather_data['forecast']['forecastday'][0]['day']['avghumidity']}%, uv: {weather_data['forecast']['forecastday'][0]['day']['uv']}, sunrise: {weather_data['forecast']['forecastday'][0]['astro']['sunrise']}, sunset: {weather_data['forecast']['forecastday'][0]['astro']['sunset']}"""
            st.session_state.weather_context_details = context_summary
            
        else:
            if not city:
                result = f"Please provide a city name."
        
        st.session_state.weather_city_context["date"] = date
        st.session_state.weather_city_context["city"] = city
    
    elif intent == "GetDetails":
        if "weather_context_details" in st.session_state and st.session_state.weather_context_details:
            print("Using existing weather context for follow-up.")
            followup_prompt = [
            ("system", f"""You are a weather assistant. Use the current weather context to answer user questions.
            Current context:
            {st.session_state.weather_context_details}"""),
            ("system", "If the user asks about a different location or date, then tell them to confirm their request so that you call an API for the desired city and date."),
            ("user", input_text),
            ("assistant", "The weather details...")
            ]

            # followup_prompt += st.session_state.conversation_history[-6:]
            # followup_prompt.append(("user", input_text))

            followup_prompt = ChatPromptTemplate.from_messages(followup_prompt)
            followup_chain = followup_prompt | llm | output_parser
            result = followup_chain.invoke({})
            # Mr. ChatGPT, please help here.
            # If the result is about getting the weather for a different city (new query for GetWeather), then we need to go through the same process as the GetWeather intent
            print(f'\n\n\n\nfollowup prompt: {followup_prompt}')
            print(f'\n\nfollowup prmopt result: {result}')
        else:
            print("No existing weather context found. Asking for city and date.")
            result = "Please provide the city and date for the weather details."
    elif intent == "Other":
        print("Intent is Other. No specific action required.")
        result = "Your response has been noted, but it does not pertain to weather inquiries. Please ask about the weather or related details."
 
 
    escaped_result = result.replace("{", "{{").replace("}", "}}")
    st.session_state.conversation_history.append(("assistant", escaped_result))
       
# Display the full chat history
for role, message in st.session_state.conversation_history:
    with st.chat_message(role):
        st.markdown(message)