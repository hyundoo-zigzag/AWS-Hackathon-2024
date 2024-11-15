import streamlit as st
import os
import pandas as pd
from functools import partial
from utils import languages, get_avatars
from bedrock import Bedrock
from polly import Polly
from scraper import FierfoxScraper
from google_api import GoogleMapsAPI
from PIL import Image
from script import hello_script_dict, found_script_dict


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
        message_from_dict({"role": "assistant", "content": found_script_dict[st.session_state["language"].format(name=name)], "attr":"place" , "data":place_id})
        content = st.session_state['scraper'].crawl_info(name)
        summary = st.session_state['bedrock'].get_summary(content)
        audio = st.session_state['polly'].get_polly_output(summary)
        message_from_dict({"role": "assistant", "content": summary, "attr":"audio", "data":audio})

def text_search(query):
    name = st.session_state['bedrock'].get_image_title_result(query)
    st.session_state['scraper'].text_search(name)
    st.session_state['init'] = False
    place_id = st.session_state["google_maps"].get_place_id_from_name(name)
    st.session_state['place_id'] = place_id
    message_from_dict({"role": "assistant", "content": found_script_dict[st.session_state["language"]].format(name=name), "attr":"place" , "data":place_id})
    content = st.session_state['scraper'].crawl_info(name)
    summary = st.session_state['bedrock'].get_summary(content)
    audio = st.session_state['polly'].get_polly_output(summary)
    message_from_dict({"role": "assistant", "content": summary, "attr":"audio", "data":audio})

def message_from_dict(message_dict):
    role = message_dict["role"]
    if role == 'assistant':
        avatar = st.session_state['bot_avatar']
    else:
        avatar = st.session_state['user_avatar']
    message_dict['avatar'] = avatar
    st.session_state['messages'] = st.session_state.get('messages', []) + [message_dict]

def initialize_session():
    st.session_state['init'] = True
    st.session_state['scraper'] = FierfoxScraper()
    st.session_state['bedrock'] = Bedrock(lang=st.session_state['language'])
    st.session_state['polly'] = Polly(st.session_state['language'])
    st.session_state['google_maps'] = GoogleMapsAPI(api_key='AIzaSyATZi8wF2BL2VET2w2fiJnAvsl5Dt6b520', lang=st.session_state['language'])
    st.session_state['messages'] = []
    
    bot_avatar, user_avatar = get_avatars()
    st.session_state['bot_avatar'] = bot_avatar
    st.session_state['user_avatar'] = user_avatar

def find_nearby_places(coordinate, type=None, keyword=None, radius=3000):
    result = []
    places = st.session_state['google_maps'].get_nearby_places(
        location=coordinate,
        place_type=type,
        keyword=keyword,
        radius=radius
    )
    if places is not None:
        for place in places:
            print(place)
            info = place['geometry']['location']
            info['place_id'] = place['place_id']
            info['이름'] = place['name']
            info['별점'] = place.get('rating', '별점 없음')
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
            direction_url = f"https://www.google.com/maps/dir/?api=1&origin_place_id={coordinate}&destination={info['lat']},{info['lng']}&origin_place_id={st.session_state['place_id']}&destination_place_id={place['place_id']}&mode=transit"
            info['url'] = direction_url
            result.append(info)
    result_pd = pd.DataFrame(result)
    message_from_dict({"role": "assistant", "content": f"요청하신 결과입니다.", "attr":"place_df" , "data":result_pd})

st.set_page_config(layout="wide")

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

col1, col2, col3 = st.columns((1, 4, 1))
with col2:
    st.image(Image.open("logo.png"))
    st.caption("🚀 N개국어 가이드와 함께하는 여행")
if len(st.session_state['messages'])==0:
    message_from_dict({"role": "assistant", "content": hello_script_dict[st.session_state["language"]], 'attr':'welcome'})

if prompt := st.chat_input():
    message_from_dict({"role": "user", "content": prompt})
    response = st.session_state['bedrock'].get_answer(st.session_state['messages'][1:])
    if response['stopReason']=='end_turn':
        answer = response['output']['message']['content'][0]['text']
        message_from_dict({"role": "assistant", "content": answer})
    elif response['stopReason']=='tool_use':
        toolUse = list(filter(lambda x:'toolUse' in x, response["output"]['message']['content']))[0]['toolUse']
        if toolUse['name']=='call_rag':
            question = toolUse['input']['question']
            doc_loaded, answer = st.session_state['bedrock'].get_insurance_answer(question)
            if doc_loaded:
                message_from_dict({"role": "assistant", "content": answer})
            else:
                message_from_dict({"role": "assistant", "content": answer, "attr":'insurance'})
        elif toolUse['name']=='text_input':
            query = toolUse['input']['query']
            text_search(query)
            

st.markdown(
    """
<style>
    .st-emotion-cache-1c7y2kd {
        flex-direction: row-reverse;
        text-align: right;
    }
</style>
""",
    unsafe_allow_html=True,
)

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
                            '주변 맛집',
                            on_click=partial(find_nearby_places, coordinate=coordinate, keyword='음식점'),
                            use_container_width=True,
                            icon='🍽️'
                        )
                    with col2:
                        st.button(
                            '주변 카페',
                            on_click=partial(find_nearby_places, coordinate=coordinate, keyword='카페'),
                            use_container_width=True,
                            icon='☕'
                        )
                    with col3:
                        st.button(
                            '주변 호텔',
                            on_click=partial(find_nearby_places, coordinate=coordinate, keyword='숙박업소'),
                            use_container_width=True,
                            icon='🏨'
                        )
                    with col4:
                        st.button(
                            '주변 가볼만한 곳',
                            on_click=partial(find_nearby_places, coordinate=coordinate, type='tourist_attraction', radius=5000),
                            use_container_width=True,
                            icon='🤩'
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