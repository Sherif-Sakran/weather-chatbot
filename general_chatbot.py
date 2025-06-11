from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGSMITH_TRACING"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGSMITH_API_KEY")

## Prompt Template
prompt=ChatPromptTemplate.from_messages(
    [
        ("system","You are a helpful assistant. Please response to the user queries. For any query about 'weather', you should start with 'The weather is very calm, and the world is queit.'"),
        ("user","Question:{question}")
    ]
)

## streamlit framework
st.title('Langchain Demo With LLAMA3.2')
input_text=st.text_input("Chat with your LLM", placeholder="Ask me anything...")

# ChatOllama
llm=ChatOllama(model="llama3.2")

output_parser=StrOutputParser()

chain= prompt | llm | output_parser

if input_text:
    st.write(chain.invoke({"question":input_text}))
