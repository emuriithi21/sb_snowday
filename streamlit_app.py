import streamlit as st
import random
import time
from snowflake.core import Root
from snowflake.snowpark.context import get_active_session
session = get_active_session()
from snowflake.cortex import Complete
root = Root(session)


policy_search_service = (root
  .databases["TB_101"]
  .schemas["CORTEX_AI"]
  .cortex_search_services["POLICY_DOCS_SEARCH_SVC"]
)



def get_chat_history():
    """
    Retrieve the chat history from the session state 
    
    """
   
    return st.session_state.messages

def get_cortex_search_question(user_question):
    """
        Creates a question sent to cortex search based on the user input and the chat history
        
    """
    chat_history = get_chat_history()
    prompt = f"""
        [INST]
        Based on the chat history below and the question, generate a query that extend the question
        with the chat history provided. This question will be passed to a retreival engine to extract the right text to answer the question that the user is asking.
        The query should be in natural language. 
        Answer with only the query. Do not add any explanation.

        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {user_question}
        </question>
        [/INST]
    """
    cortex_search_question = Complete('llama3.1-70b', prompt)

    return cortex_search_question

st.title("Standard Bank Insurance Policy Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
      
    greeting = "Hi, How can I help you today?"
    st.session_state.messages.append({"role": "assistant", "content": greeting })

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
# Accept user input
if user_question := st.chat_input("What is your question?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_question})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_question)

        # based on the chat history and the user's question, get the right question to ask cortex search
        cortex_search_prompt=get_cortex_search_question(user_question)
        
        # retreive  a maximum of 20 chunks
        resp = policy_search_service.search(
          query=cortex_search_prompt,
          columns=["CHUNK", "DOCUMENT_NAME"],
          
          limit=20)
        
        # get the chat history to pass to the llm
        chat_history = get_chat_history()
        results= resp.results
        context_str = ""
        for i, r in enumerate(results):
            context_str += f"#### Context document: {i+1}, Document name: {r['DOCUMENT_NAME']} : \n{r['CHUNK']} \n" + "\n"

        context= context_str

        # prompt engineering by oassing the chat history, the context and the user's question
        prompt = f"""
            [INST]
            You are a helpful AI chat assistant with RAG capabilities. When a user asks you a question,
            you will also be given context provided between <context> and </context> tags. Use that context
            with the user's chat history provided in the between <chat_history> and </chat_history> tags
            to provide a summary that addresses the user's question. Theuser's question is between the  <user_question> and </user_question> tags
            
            Ensure the answer is detailed and directly relevant to the user's question.

            If the user asks a generic question which cannot be answered with the given context or chat_history,
            just say "I don't know the answer to that question.

            Provide the answer in markdown format, do not include titles and subtitles 

            Don't saying things like "according to the provided context".

            <chat_history>
            {chat_history}
            </chat_history>
            <context>
            {context}
            </context>
            <question>
            {user_question}
            </question>
            [/INST]
            Answer:
        """

        
    with st.spinner("Searching..."):
        
        # pass the engineered prompt to the llm, in this case llama
        response= Complete('mistral-large2',prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        
        st.write(response)
        
    st.session_state.messages.append({"role": "assistant", "content": response})