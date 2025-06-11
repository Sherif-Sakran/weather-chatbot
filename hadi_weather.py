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

print(examples[:150])

## Prompt Template
prompt=ChatPromptTemplate.from_messages(
    [
        ("system","""You are an NLU module. Extract the intent and slot values from user messages. There are some examples of user messages below.
        {examples}
         I want you to return only the intent and slot values in JSON format. If there is a value missing, you should ask the user to provide it.
         """),
        ("user","Question:{question}")
    ]
)

## streamlit framework
st.title('Weather Chatbot with LLAMA3.2')
input_text=st.text_input("Chat with me!", placeholder="Ask me about the weather...")

# ChatOllama
llm=ChatOllama(model="llama3.2")

output_parser=StrOutputParser()

chain= prompt | llm | output_parser

if input_text:
    st.write(chain.invoke({"examples": examples, "question": input_text}))
