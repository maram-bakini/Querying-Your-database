from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import google.generativeai as genai
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def init_database(db_user: str,db_password: str,db_host: str,db_name: str) -> SQLDatabase:
    db = SQLDatabase.from_uri(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}")
    return db 
    

def get_schema(db):
    return db.get_table_info()


def get_sql_chain(schema,chat_history,question):
    template= """
    
    You are an expert in converting English questions to SQL query! 
    Always ensure the SQL command is optimized and doesn't have any unnecessary keywords.
    Based on the table schema below, write an sql query that would answer the user's question.Take the conversation history into account.
    
    <SCHEMA>{schema}</SHEMA>
    Conversation History: {chat_history}
    
    
    Please generate the most efficient SQL query and nothing else without unnecessary comments or SQL keywords like 'sql'.
    Please ensure that the response does not start or contain "'''". 
    
    
    For example:
    Example 1: How many records are present? 
    SQL: SELECT COUNT(*) FROM <table_name>;
    
    Example 2: Show all students in the Data Science class.
    SQL: SELECT * FROM STUDENT WHERE CLASS='Data Science';
    
    Your turn:
    
    Question:{question}
    SQL Query:

    """   
    return template.format(schema=schema, chat_history=chat_history, question=question)
    
    
def Get_NL_response(sql_query,schema,sql_response):
    template="""
    You are an expert in SQL! 
    You have to convert the result of the SQL query execution into human language response.
    Based on the table schema below, the user query, the sql response transform the sql response into human language response.Take the conversation history into account.
    
    <SCHEMA>{schema}</SHEMA>
    
    Sql_execution_response:{sql_response}
    
    Your turn:
    
    Sql query:{sql_query}
    Response:
    
    """
    return template.format(sql_query=sql_query,schema=schema,sql_response=sql_response)
     


if "chat_history" not in st.session_state:
    st.session_state.chat_history=[
        AIMessage("Hello! I'm a SQL assistant. Ask me anything about your database."),
        
    ]
    
def get_gemini_query_explanation(query,prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[1], query])
    return response.text
     
def get_gemini_response(question, prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content([prompt, question])
        return response.text.strip()  
    except Exception as e:
        st.error(f"Error generating SQL query: {e}")
        return None
    
def get_human_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text.strip() 
    except Exception as e:
        st.error(f"Error generating Human response: {e}")
        return None



# Streamlit app
st.set_page_config(page_title="SQL Query Generator with LLM")
st.header("Query Your Database ")


with st.sidebar:
    st.subheader("Database Connection")
    
    st.text_input("Host",value="localhost",key="host")
    st.text_input("User",key="user")
    st.text_input("Password",type="password",key="password")
    st.text_input("Database",key="database")
    
    if st.button("Connect"):
        with st.spinner("Connecting to the database..."):
            db= init_database(
                st.session_state["user"],
                st.session_state["password"],
                st.session_state["host"],
                st.session_state["database"],
            )
            
            st.session_state.db=db
            st.success("Connected to the database !")
            

for message in st.session_state.chat_history:
    if isinstance(message,AIMessage):
        with st.chat_message("ai"):
            st.markdown(message.content)
    elif isinstance(message,HumanMessage):
        with st.chat_message("human"):
            st.markdown(message.content)

if "db" in st.session_state:
    schema = get_schema(st.session_state.db)
user_query=st.chat_input("Type a message...")


if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("human"):
        st.markdown(user_query) 
    with st.chat_message("ai"):
        
        prompt=get_sql_chain(schema,st.session_state.chat_history,user_query)
        sql_query=get_gemini_response(user_query, prompt)
        sql_response=st.session_state.db.run(sql_query)
        response_prompt=Get_NL_response(sql_query,schema,sql_response)
        response=get_human_response(response_prompt)
        st.markdown(response)
        
    st.session_state.chat_history.append(AIMessage(content=response))

