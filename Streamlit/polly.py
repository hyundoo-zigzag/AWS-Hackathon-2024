import boto3

voice_dict = {
    'Dutch':'Laura',
    'Norwegian':'Ida',
    'Danish':'Sofie',
    'German':'Vicki',
    'Russian':'Tatyana',
    'Spanish':'Elena',
    'English':'Kimberly',
    'Italian':'Bianca',
    'Japanese':'Kazuha',
    'Chinese':'Zhiyu',
    'Czech':'Jitka',
    'Turkish':'Burcu',
    'Portuguese':'Ines',
    'Polish':'Ola',
    'French':'Lea',
    'Finnish':'Suvi',
    '한국어':'Seoyeon',
    'Hindi':'Kajal'
}


class Polly:
    def __init__(self, lang):
        self.lang = lang
        self.voice = voice_dict[lang]
        self.polly_client = boto3.client('polly', region_name="ap-northeast-2")
        
    def get_polly_output(self, text):
        response = self.polly_client.synthesize_speech(
            Engine="neural",
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.voice
        )
        return response['AudioStream'].read()