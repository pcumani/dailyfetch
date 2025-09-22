import os
import logging
import requests
import streamlit as st

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Dailyfetch",
    page_icon=":newspaper:",
    layout="wide",
)

if 'fetched_news' not in st.session_state:
    st.session_state.fetched_news = ''

def reset_page():
    
    st.session_state.fetched_news = ''


def fetch_news(model, api_key, sources, categories):
    api_url = 'http://agent:80'
    set_model = requests.post(f"{api_url}/set_model/",json={"model": "GOOGLE" if 'GOOGLE' in model.upper() else "OPENAI", 
                                                            "api_key": api_key if api_key !='' else None})
    if set_model.status_code != 201:
        st.session_state.fetched_news = f"There was an error while initialising the model: {set_model.text}"
    else:
        endpoint = f'{api_url}/summarize_news/?'
        if len(categories)>0:
            endpoint += 'news_categories='+'&news_categories='.join(categories)
        if len(sources)>0:
            srcs = 'news_sources='+'&news_sources='.join(sources)
            endpoint = endpoint + srcs if endpoint.endswith('?') else endpoint + '&' + srcs
        news = requests.post(endpoint)

        if set_model.status_code != 200:
            st.session_state.fetched_news = f"There was an error summarizing the news: {news.text}"
        else:
            st.session_state.fetched_news = news.text

_, cent_co,_ = st.columns(3)
with cent_co:
    st.image(str(os.path.join("..", "assets", "logo.png")), width=600)


cols = st.columns([1, 3])

with cols[0]:
    model = st.selectbox("Which LLM model would you like to use?", ("Google Gemini 2.5-flash", "OpenAI gpt 4o-mini"),)
    api_key = st.text_input("Enter the API key to use the model (if empty the corresponding environment variable will be used)", type="password")

    sources = st.multiselect("From which sources should I retrieve the news?", ["reddit", "hacker news"], default=["reddit"],)
    categories = st.multiselect("Which type of news are you interested in?", ["technology", "sport", "general"], default=["technology"],)
    left_co, cent_co = st.columns([3,1])
    with cent_co:
        st.button("Clear", on_click=reset_page, type="primary")
    with left_co:
        st.button("Fetch me some news!", on_click=fetch_news, args=[model, api_key, sources, categories], type="primary")

with cols[1]:
    t = st.empty()
    t.write(f'{st.session_state.fetched_news}')

