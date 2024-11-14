import re

languages = [
    'Dutch', 'Norwegian', 'Danish', 'German', 'Russian', 'Spanish', 'English', 'Italian', 'Japanese',
    'Chinese', 'Czech', 'Turkish', 'Portuguese', 'Polish', 'French', 'Finnish', '한국어', 'Hindi'
]
bot_avatar = 'data:image/jpeg;base64,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'

def clean_title(title):
    """출처 정보를 제거하는 함수"""
    # 출처 정보(예: "네이버 블로그", "출처:", "Facebook", "Instagram") 등을 제거하는 정규 표현식
    title = re.sub(r'\[.*\]|\s*(네이버\s*블로그|Tripadvisor|트립어드바이저|다이닝코드|빅데이터|맛집검색|Facebook|Instagram|위키피디아|출처:.*|출처\s*.*)', '', title)  # 출처 부분 제거
    return title.strip()