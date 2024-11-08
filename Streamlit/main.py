import streamlit as st
import base64
import os
from utils import languages, bot_avatar
from bedrock import Bedrock
from polly import Polly
from scraper import FierfoxScraper

def init_insurance_rag():
    uploaded_file = st.session_state.get('insurance')
    if uploaded_file != None:
        st.session_state['bedrock'].init_rag(uploaded_file)

def image_welcome():
    uploaded_file = st.session_state.get('uploaded_file')
    if uploaded_file != None:
        message_from_dict({"role": "user", "content": uploaded_file.name})        
        with open('./temp.png', 'wb') as f:
            f.write(uploaded_file.getbuffer())
            name = st.session_state['scraper'].image_search(os.path.abspath('./temp.png'))
        st.session_state['init'] = False
        message_from_dict({"role": "assistant", "content": f"{name}를(을) 찾았습니다. 정보를 찾는 중이에요."})
        
        content = st.session_state['scraper'].crawl_wiki()
        summary = st.session_state['bedrock'].get_summary(content)
        audio = st.session_state['polly'].get_polly_output(summary)
        message_from_dict({"role": "assistant", "content": summary, "attr":"audio", "data":audio})

def message_from_dict(message_dict):
    role = message_dict["role"]
    if role == 'assistant':
        avatar = bot_avatar
    else:
        avatar = None
    message_dict['avatar'] = avatar
    st.session_state['messages'] = st.session_state.get('messages', []) + [message_dict]

def initialize_session():
    st.session_state['init'] = True
    st.session_state['scraper'] = FierfoxScraper()
    st.session_state['bedrock'] = Bedrock()
    st.session_state['polly'] = Polly(st.session_state['language'])

with st.sidebar:
    language = st.selectbox(
        '사용자의 언어를 선택하세요',
        options=languages, index=16, on_change=initialize_session,
        key='language'
    )

if 'init' not in st.session_state:
    initialize_session()

st.title("여행찬호")
st.caption("🚀 수다쟁이 가이드와 함께하는 여행")
if "messages" not in st.session_state:
    message_from_dict({"role": "assistant", "content": "안녕하세요! 여행찬호입니다. 이미지를 입력하거나 명소의 이름을 입력해주세요", 'attr':'welcome'})

if prompt := st.chat_input():
    message_from_dict({"role": "user", "content": prompt})
    response = st.session_state['bedrock'].get_answer(st.session_state['messages'][1:])
    if response['stopReason']=='end_turn':
        answer = response['output']['message']['content'][0]['text']
        message_from_dict({"role": "assistant", "content": answer})
    elif response['stopReason']=='tool_use':
        question = list(filter(lambda x:'toolUse' in x, response["output"]['message']['content']))[0]['toolUse']['input']['question']
        doc_loaded, answer = st.session_state['bedrock'].get_insurance_answer(question)
        if doc_loaded:
            message_from_dict({"role": "assistant", "content": answer})
        else:
            message_from_dict({"role": "assistant", "content": answer, "attr":'insurance'})

for msg in st.session_state['messages']:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.write(msg["content"])
            if msg.get('attr') == 'insurance':
                st.file_uploader(
                    label='보험약관 업로드',
                    label_visibility='collapsed',
                    key='insurance',
                    on_change=init_insurance_rag
                )
            elif msg.get('attr') == 'welcome' and st.session_state['init']:
                st.file_uploader(
                    label='여행관련 사진',
                    label_visibility='collapsed',
                    type=['png', 'jpg', 'jpeg'],
                    key='uploaded_file',
                    on_change=image_welcome
                )
            elif msg.get('attr') == 'audio':
                st.audio(msg['data'])