import re
from PIL import Image

languages = [
    'Dutch', 'Norwegian', 'Danish', 'German', 'Russian', 'Spanish', 'English', 'Italian', 'Japanese',
    'Chinese', 'Czech', 'Turkish', 'Portuguese', 'Polish', 'French', 'Finnish', '한국어', 'Hindi'
]


def get_avatars():
    bot_avatar = Image.open('bot.png')
    user_avatar = Image.open('user.png')
    return bot_avatar, user_avatar

def clean_title(title):
    """출처 정보를 제거하는 함수"""
    # 출처 정보(예: "네이버 블로그", "출처:", "Facebook", "Instagram") 등을 제거하는 정규 표현식
    title = re.sub(r'\[.*\]|\s*(네이버\s*블로그|Tripadvisor|트립어드바이저|다이닝코드|빅데이터|맛집검색|Facebook|Instagram|위키피디아|출처:.*|출처\s*.*)', '', title)  # 출처 부분 제거
    return title.strip()