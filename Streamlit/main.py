import streamlit as st
import base64
import os
from utils import languages, bot_avatar
from bedrock import Bedrock
from polly import Polly
from scraper import FierfoxScraper
from anthropic import AnthropicBedrock

def message_from_dict(message_dict):
    role = message_dict["role"]
    if role == 'assistant':
        avatar = bot_avatar
        # avatar = None
    else:
        avatar = None
    message_dict['avatar'] = avatar
    st.session_state['messages'] = st.session_state.get('messages', []) + [message_dict]
    for msg in st.session_state['messages']:
        st.chat_message(msg["role"], avatar=msg["avatar"]).write(msg["content"])

if 'flag' not in st.session_state:
    st.session_state['flag'] = False

with st.sidebar:
    language = st.selectbox(
        '사용자의 언어를 선택하세요',
        options=languages, index=16, on_change=None
    )

scraper = FierfoxScraper()
bedrock = Bedrock()
polly = Polly(language)

st.title("여행찬호")
st.caption("🚀 수다쟁이 가이드와 함께하는 여행")
if "messages" not in st.session_state:
    message_from_dict({"role": "assistant", "content": "안녕하세요! 여행찬호입니다. 이미지를 입력하거나 명소의 이름을 입력해주세요"})

uploaded_file = st.file_uploader(label='', disabled=st.session_state.flag, type=['png', 'jpg', 'jpeg'])
if uploaded_file:
    with open('./temp.png', 'wb') as f:
        f.write(uploaded_file.getbuffer())
        name = scraper.image_search(os.path.abspath('./temp.png'))
    st.session_state['flag'] = True
    message_from_dict({"role": "assistant", "content": f"{name}를(을) 찾았습니다. 정보를 찾는 중이에요."})
    content = scraper.crawl_wiki()
    summary = bedrock.get_summary(content)
    audio = polly.get_polly_output(summary)
    st.audio(audio)

if prompt := st.chat_input():
    message_from_dict({"role": "user", "content": prompt})
    output = bedrock.get_answer(st.session_state['messages'][1:])
    message_from_dict({"role": "assistant", "content": output})

print(st.session_state['messages'])