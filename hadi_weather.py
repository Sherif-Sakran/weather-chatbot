from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGSMITH_TRACING"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGSMITH_API_KEY")

directory = '..\examples'
examples = ""

counter = 1
for filename in os.listdir(directory):
    if filename.endswith('.txt'):
        examples += f"Example {counter}:\n"
        counter += 1
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            examples += file.read()
examples = examples.replace("{", "{{").replace("}", "}}")
# print(examples[:150])

## streamlit framework
st.title('Weather Chatbot with LLAMA3.2')
input_text=st.text_input("Chat with me!", placeholder="Ask me about the weather...")

# ChatOllama
llm=ChatOllama(model="llama3.2")

output_parser=StrOutputParser()

# chain= prompt | llm | output_parser

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""


if input_text:
    st.session_state.conversation_history.append(("user", input_text))
    
    full_prompt = [
        ("system","""You are an NLU module specialized in extracting information from the prompt. Extract the intent and slot values from user messages. There are some examples of user messages below. """ + examples + """\n\n You should return only the intent and slot values. You do NOT need to interpret the message or have a conversation about the weather. ONLY extract the intent and slot values. If there is a value missing, you should ask the user to provide it. When you have received the full information, return the intent and slot in JSON format. Do not ask about any further information. Your whole job is to EXTRACT the intent and slot values correctly and fully from the user.""")
    ] + st.session_state.conversation_history[-4:]

    prompt = ChatPromptTemplate.from_messages(full_prompt)

    chain = prompt | llm | output_parser
    result = chain.invoke({})  # No extra vars needed if it's just conversation
    escaped_result = result.replace("{", "{{").replace("}", "}}")
    st.session_state.conversation_history.append(("assistant", escaped_result))
    
    st.write(result)