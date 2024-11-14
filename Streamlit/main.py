import streamlit as st
import os
import pandas as pd
from functools import partial
from utils import languages, bot_avatar
from bedrock import Bedrock
from polly import Polly
from scraper import FierfoxScraper
from google_api import GoogleMapsAPI


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
        if type(name)==list:
            name = st.session_state['bedrock'].get_image_title_result(name)
            st.session_state['scraper'].text_search(name)
        st.session_state['init'] = False
        place_id = st.session_state["google_maps"].get_place_id_from_name(name)
        st.session_state['place_id'] = place_id
        message_from_dict({"role": "assistant", "content": f"{name}를(을) 찾았습니다. 정보를 찾는 중이에요.", "attr":"place" , "data":place_id})
        
        content = st.session_state['scraper'].crawl_info(name)
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
    st.session_state['bedrock'] = Bedrock(lang=st.session_state['language'])
    st.session_state['polly'] = Polly(st.session_state['language'])
    st.session_state['google_maps'] = GoogleMapsAPI('AIzaSyATZi8wF2BL2VET2w2fiJnAvsl5Dt6b520')
    st.session_state['messages'] = []

def find_nearby_places(coordinate, type, radius=3000):
    result = []
    places = st.session_state['google_maps'].get_nearby_places(
        location=coordinate,
        place_type=type,
        radius=radius
    )
    if places is not None:
        for place in places:
            info = place['geometry']['location']
            info['place_id'] = place['place_id']
            info['이름'] = place['name']
            info['별점'] = place['rating']
            address, reviews = st.session_state['google_maps'].get_place_details(
                place['place_id']
            )
            if address is not None:
                info['주소'] = address
                summarized_review = st.session_state['bedrock'].get_review_summary(reviews)
                if summarized_review is not None:
                    info['요약된 리뷰'] = summarized_review
                else:
                    info['요약된 리뷰'] = '리뷰 없음'
            direction_url = f"https://www.google.com/maps/dir/?api=1&origin={coordinate}&destination={info['lat']},{info['lng']}&mode=transit"
            info['url'] = direction_url
            result.append(info)
    result_pd = pd.DataFrame(result)
    message_from_dict({"role": "assistant", "content": f"요청하신 결과입니다.", "attr":"place_df" , "data":result_pd})

with st.sidebar:
    language = st.selectbox(
        '사용자의 언어를 선택하세요',
        options=languages,
        index=16,
        on_change=initialize_session,
        key='language'
    )

if 'init' not in st.session_state:
    initialize_session()

st.title("여행찬호")
st.caption("🚀 수다쟁이 가이드와 함께하는 여행")
if len(st.session_state['messages'])==0:
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
                    type=['pdf'],
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
                st.audio(
                    msg['data']
                )
            elif msg.get('attr') == 'place':
                if msg['data'] is not None:
                    coordinate = st.session_state['google_maps'].get_lat_lng_from_place_id(place_id=msg["data"])
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.button(
                            '주변 맛집 정보 찾기',
                            on_click=partial(find_nearby_places, coordinate=coordinate, type='restaurant')
                        )
                    with col2:
                        st.button(
                            '주변 카페 찾기',
                            on_click=partial(find_nearby_places, coordinate=coordinate, type='cafe')
                        )
                    with col3:
                        st.button(
                            '주변 호텔 찾기',
                            on_click=partial(find_nearby_places, coordinate=coordinate, type='hotel')
                        )
                    with col4:
                        st.button(
                            '주변 가볼만한 곳',
                            on_click=partial(find_nearby_places, coordinate=coordinate, type='tourist_attraction', radius=5000)
                        )
            elif msg.get('attr') == 'place_df':
                st.dataframe(
                    msg['data'],
                    hide_index=True,
                    column_config={
                        'lat':None,
                        'lng':None,
                        'place_id':None,
                        'url': st.column_config.LinkColumn(
                            "경로 안내", display_text="링크"
                        )
                    }
                )