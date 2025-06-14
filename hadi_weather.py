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
    # Extract intent
    intent_match = re.search(r"Intent:\s*(\w+)", text)
    intent = intent_match.group(1) if intent_match else None

    # Extract city
    city_match = re.search(r"'city':\s*\[\s*'([^']+)'\s*\]", text)
    city = city_match.group(1) if city_match else None

    # Extract date
    date_match = re.search(r"'date':\s*\[\s*'([^']+)'\s*\]", text)
    date = date_match.group(1) if date_match else None

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
    st.session_state.weather_city_context = {"city": None, "date": None}

def k_to_c(k): return round(k - 273.15, 1)



# Ask for new input
input_text = st.chat_input("Ask me about the weather...")

if input_text:
    st.session_state.conversation_history.append(("user", input_text))
    
    full_prompt = [
        ("system","""You are an NLU module specialized in extracting information from the prompt to call a weather forecast API. Your role is to extract the intent and slot values from the user messages. The intent and slots will be used to call an api for the weather to get the information. You should NOT answer the questions about weather yourself. Your role is only to extract the required information for the weather API. You should extract one of two intents:
         1) GetWeather: This will be any question about the weather in any way. The user just provides both the city and date so that you can answer them. GetWeather has two slots: `city` (could be any city) and `date` (could be any date). When you have received the full information, return the intent and slot in JSON format. Do not ask about any further information. Your whole job is to EXTRACT the intent and slot values correctly and fully from the user. After that, there will be a call to the weather API to get the information using the `city` and `date` slots that you will be available for you for later interactions. Follow the following rules:
         - If the user does not provide a date, ask the user for the date. 
         - If the user does not provide a city, ask the user for the city. 
         - Return the intent and slots in JSON format ONLY IF the user provides both slots. 
         - If the user does not provide any of the required slots, do not return any JSON yet. Instead, ask the user for ONLY the missing slot.
         Here is an example of a user message:""" + get_weather_examples + """
         2) GetDetails: this intent has one slot: `request` (could only be 'humidity', 'wind'). This intent is used to get details from the weather api response that you will receive after the call of GetWeather api. Your only task is to know what detail the using is asking for. You should not ask the user for any further information. You should return the intent and slot in JSON format. Here is an example of a user message: """ + get_details_examples)
    ] + st.session_state.conversation_history[-6:]

    prompt = ChatPromptTemplate.from_messages(full_prompt)
    for role, content in full_prompt:
        print(f"*{role.upper()}*: {content}\n")
    chain = prompt | llm | output_parser
    result = chain.invoke({})  # No extra vars needed if it's just conversation

    print(f'res: {result}')
    intent, city, date = extract_info_from_response(result)
    print(f"Extracted intent: {intent}, city: {city}, date: {date}")
    context_summary = ""
    if intent == "GetWeather":
        if city and date:
            print(f"Calling weather forecast API for city: {city}, date: {date}")
            date = dateparser.parse(date)
            if not date:
                print(f"Invalid date format: {date}. Please provide a valid date.")
                result = "I need a valid date to provide the weather information. Please provide a valid date."

            else:
                print(f"Parsed date: {date}")
                lat, lon = get_lat_lon(city)
                weather_data = get_weather(lat, lon, date)
                print(f"Weather data: {weather_data}")
                past_forecast = " (note that it is a weather in the past)" if date.date() < datetime.today().date() else ""

                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"""You are a weather assistant. Write the weather forecast in summary{past_forecast}. Here is the information: city: {city}, date: {date.strftime('%Y-%m-%d')}, max_temperature: {weather_data['forecast']['forecastday'][0]['day']['maxtemp_c']}°C, min_temperature: {weather_data['forecast']['forecastday'][0]['day']['mintemp_c']}°C, average_temperature: {weather_data['forecast']['forecastday'][0]['day']['avgtemp_c']}°C"""),
                    ("user", f"Summarize the weather forecast for {city} on {date.strftime('%Y-%m-%d')}."),
                    ("assistant", "The weather forecast is as follows:"),
                ])
                print(f"Prompt: {prompt}")
                chain = prompt | llm | output_parser
                # chain = prompt | llm
                result = chain.invoke({})
                print(f'Weather summary: {result}')
                # result = f"""The weather in {city} is {weather_data['weather'][0]['description']}
                # with a temperature of {weather_data['main']['temp'] - 273.15:.1f}°C."""

                context_summary = f"""
                Weather context for further GetDetails interactions for {city} on {date}:
                max_temperature: {weather_data['forecast']['forecastday'][0]['day']['maxtemp_c']}°C, min_temperature: {weather_data['forecast']['forecastday'][0]['day']['mintemp_c']}°C, average_temperature: {weather_data['forecast']['forecastday'][0]['day']['avgtemp_c']}°C, maxwind_mph: {weather_data['forecast']['forecastday'][0]['day']['maxwind_mph']} mph, totalprecip_mm: {weather_data['forecast']['forecastday'][0]['day']['totalprecip_mm']} mm, avgvis_km: {weather_data['forecast']['forecastday'][0]['day']['avgvis_km']} km, avghumidity: {weather_data['forecast']['forecastday'][0]['day']['avghumidity']}%, uv: {weather_data['forecast']['forecastday'][0]['day']['uv']}, sunrise: {weather_data['forecast']['forecastday'][0]['astro']['sunrise']}, sunset: {weather_data['forecast']['forecastday'][0]['astro']['sunset']}

                Use this information to answer any further questions about the weather in {city} on {date}. If the user asks about a different location or date, then follow their request to get weather for the desired city and date.
                """
                st.session_state.weather_context_details = context_summary
            
        else:
            if not city and date:
                result = f"I need to know the city for which you want the weather information. Please provide a city name."
            elif not date and city:
                result = f"I need to know the date for which you want the weather information. Please provide a date."
        
        st.session_state.weather_city_context["date"] = date
        st.session_state.weather_city_context["city"] = city
    
    elif "weather_context_details" in st.session_state and st.session_state.weather_context_details:
        print("Using existing weather context for follow-up.")
        followup_prompt = [
        ("system", f"""You are a weather assistant. Use the weather context below to answer the user's question about the weather of {st.session_state.weather_city_context['city']} in {st.session_state.weather_city_context['date']}. If the user asks about a different location or date, you must help them by extracting the desired city and date so that you can call the weather forecast API. In this case of calling the weather forecast API, ask the user to confirm their intention to get the weather for the specified city and date. If the user did not specify the city, assume it is the same city as the previous weather context. If the user did not specify the date, assume it is the same date as the previous weather context."""),
        ("system", st.session_state.weather_context_details),
        ]
        followup_prompt += st.session_state.conversation_history[-6:]
        followup_prompt.append(("user", input_text))
        followup_prompt = ChatPromptTemplate.from_messages(followup_prompt)
        followup_chain = followup_prompt | llm | output_parser
        result = followup_chain.invoke({})
        for role, content in followup_prompt.messages:
            print(f"@{role}@: {content}\n")      
        print(f'Follow-up result: {result}')

    # else:
    #     result = "I couldn't understand your request. Please try again."
    escaped_result = result.replace("{", "{{").replace("}", "}}")
    st.session_state.conversation_history.append(("assistant", escaped_result))
       
    # with st.chat_message("assistant"):
    #     st.markdown(result)

# Display the full chat history
for role, message in st.session_state.conversation_history:
    with st.chat_message(role):
        st.markdown(message)