import boto3

voice_dict = {
    '네덜란드어':'Laura',
    '노르웨이어':'Ida',
    '덴마크어':'Sofie',
    '독일어':'Vicki',
    '러시아어':'Tatyana',
    '스페인어':'Elena',
    '영어':'Kimberly',
    '이탈리아어':'Bianca',
    '일본어':'Kazuha',
    '중국어':'Zhiyu',
    '체코어':'Jitka',
    '터키어':'Burcu',
    '포르투갈어':'Ines',
    '폴란드어':'Ola',
    '프랑스어':'Lea',
    '핀란드어':'Suvi',
    '한국어':'Seoyeon',
    '힌디어':'Kajal'
}


class Polly:
    def __init__(self, lang):
        self.lang = lang
        self.voice = voice_dict[lang]
        self.polly_client = boto3.client('polly', region_name="ap-northeast-2")
        
    def get_polly_output(self, text):
        response = self.polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.voice
        )
        return response['AudioStream'].read()