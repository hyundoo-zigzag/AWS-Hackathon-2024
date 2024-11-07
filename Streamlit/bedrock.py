import boto3
import json

summarize_translate_prompt = '''
[role]
- 당신은 주어진 장소의 정보를 읽고 그 장소를 여행하는 사람에게 정보를 정리하여 전달하는 아나운서입니다.
- 정보는 한국어로 번역하여 전달합니다.
- 장소의 정보는 여행하는 사람이 흥미있어할 만한 내용을 위주로 정리합니다.
- 흥미있는 내용이 있다면 꼭 포함해주세요.

[current_year]
2024

[behavior_guidelines
- 정확한 정보만 제공하며, 문서에 없는 내용을 상상하여 답변하지 않습니다.
- '문서에에 따르면'과 같이 문서를 참고하는 것을 티내지 마세요.
- 사용자에게 바로 설명할 수 있도록 답변하세요.
- 아나운서의 대본처럼 바로 읽을 수 있게 답변하세요
'''

system_prompt = None

class Bedrock:
    def __init__(
        self,
        model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
        system_prompt=system_prompt,
        summarize_translate_prompt=summarize_translate_prompt
    ):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        self.model_id = model_id
        self.system_prompt = system_prompt,
        self.summarize_translate_prompt = summarize_translate_prompt
        
    def get_answer(self, messages):
        messages = [{'role':msg['role'], 'content':msg['content']} for msg in messages]
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                # "system": self.system_prompt,
                "messages": messages
            }  
        )
        response = self.bedrock_client.invoke_model(body=body, modelId=self.model_id)
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    
    def get_summary(self, text):
        messages = [{"role": "user", "content": text}]
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "system": self.summarize_translate_prompt,
                "messages": messages
            }  
        )
        response = self.bedrock_client.invoke_model(body=body, modelId=self.model_id)
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']