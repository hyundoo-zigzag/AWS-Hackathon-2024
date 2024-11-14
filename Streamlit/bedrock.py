import boto3
import json
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings

rag_prompt = '''
[role]
당신은 주어진 여행자보험의 약관을 읽고 사용자의 질문에 답변하는 챗봇입니다.
정보는 {lang}로 번역하여 전달합니다.

[current_year]
2024

[behavior_guidelines]
- 정확한 정보만 제공하며, 문서에 없는 내용을 상상하여 답변하지 않습니다.
- 절대 주어진 약관에 없는 내용을 상상하여 답변하지 마세요.
- 친절한 말투로 답변합니다.
- 예외는 없습니다.

{context}

'''

review_summarize_translate_prompt = '''
[role]
- 당신은 주어진 리뷰들을 모두 읽고 핵심 내용만 추려서 한 문장으로 요약합니다.
- 정보는 {lang}로 번역하여 전달합니다.

[current_year]
2024

[behavior_guidelines]
- 주어진 리뷰에 없는 내용은 요약문에 넣지 마세요.
- 리뷰가 여러 개여도 요약문은 단 하나만 작성합니다.
- 절대 요약문이 20글자를 넘으면 안됩니다.
- 간결하게 요약문만 반환하세요.
- '요악문은 다음과 같습니다'와 같은 말은 붙이지 말고 바로 요약문만 반환하세요.
- 예외는 없습니다.

[response example]
아름다운 전통 카이세키 요리. 친절하고 환영하는 직원들, 세심한 서비스. 훌륭한 식재료와 정성 가득한 요리로 고객 만족.
'''


summarize_translate_prompt = '''
[role]
- 당신은 주어진 장소의 정보를 읽고 그 장소를 여행하는 사람에게 정보를 정리하여 전달하는 아나운서입니다.
- 정보는 {lang}로 번역하여 전달합니다.
- 장소의 정보는 여행하는 사람이 흥미있어할 만한 내용을 위주로 정리합니다.
- 흥미있는 내용이 있다면 꼭 포함해주세요.

[current_year]
2024

[behavior_guidelines]
- 정확한 정보만 제공하며, 문서에 없는 내용을 상상하여 답변하지 않습니다.
- '문서에에 따르면'과 같이 문서를 참고하는 것을 티내지 마세요.
- 사용자에게 바로 설명할 수 있도록 답변하세요.
- 아나운서의 대본처럼 바로 읽을 수 있게 답변하세요
'''

agent_system_prompt = '''
[role]
- 당신은 여행자의 질문에 친절하게 답변하는 챗봇입니다.
- 당신이 할 수 있는 일은 다음과 같습니다.
    - 여행자보험과 관련된 질문을 받으면 함수를 호출합니다.
    - 관광지나 맛집, 유명한 미술품 등에 대한 질문을 받으면 함수를 호출합니다.
    - 관광지나 맛집 등의 주변 정보에 대한 질문을 받으면 함수를 호출합니다.
    - 그 외에 여행과 관련된 사용자의 질문에 답변합니다.
- 당신은 {lang}로 답변합니다.

[current_year]
2024
'''

infer_system_prompt = '''
[role]
- 당신은 주어진 검색 결과를 보고 어떤 장소 혹은 물건에 대한 결과인지 유추합니다.

[current_year]
2024

[behavior_guidelines]
- 유추한 물건 이름만 반환합니다.
- '~의', '~에 있는'과 같은 수사는 사용하지 않습니다.

[response example]
미륵사지석탑
'''

tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "call_rag",
                "description": "여행자보험과 관련된 사용자의 질문에 답변합니다.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "여행자보험과 관련된 질문 내용입니다. 보장범위나 보상금액, 보험사 정보 등이 이 내용에 해당됩니다."
                            }
                        },
                        "required": [
                            "question"
                        ]
                    }
                }
            }
        }
    ]
}

class Bedrock:
    def __init__(
        self,
        # model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
        model_id='anthropic.claude-3-haiku-20240307-v1:0',
        lang='한국어',
        agent_system_prompt=agent_system_prompt,
        summarize_translate_prompt=summarize_translate_prompt,
        review_summarize_translate_prompt=review_summarize_translate_prompt,
        infer_system_prompt=infer_system_prompt,
        tool_config=tool_config,
        insurance_rag=None,
    ):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        self.model_id = model_id
        self.agent_system_prompt = agent_system_prompt
        self.summarize_translate_prompt = summarize_translate_prompt
        self.review_summarize_translate_prompt = review_summarize_translate_prompt
        self.infer_system_prompt = infer_system_prompt
        self.tool_config = tool_config
        self.insurance_rag = insurance_rag
        self.lang=lang
        
    def get_answer(self, messages):
        messages = [{'role':msg['role'], 'content':[{"text":msg['content']}]} for msg in messages]
        messages = self.merge_continuous_message(messages)
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.agent_system_prompt.format(lang=self.lang)}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,   
            },
            toolConfig=tool_config
        )
        return response
    
    def get_summary(self, text):
        messages =  [{"role": "user", "content": [{"text":text}]}]
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.summarize_translate_prompt.format(lang=self.lang)}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,   
            }
        )
        return response['output']['message']['content'][0]['text']
    
    def get_review_summary(self, reviews):
        text = '\n\n'.join(reviews)
        messages =  [{"role": "user", "content": [{"text":text}]}]
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.review_summarize_translate_prompt.format(lang=self.lang)}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,   
            }
        )
        return response['output']['message']['content'][0]['text']
    
    def get_image_title_result(self, image_titles):
        messages =  [{"role": "user", "content": [{"text":'\n'.join(image_titles)}]}]
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.infer_system_prompt}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,   
            }
        )
        return response['output']['message']['content'][0]['text']
    
    def get_insurance_answer(self, question):
        if self.insurance_rag == None:
            return False, "여행자보험과 관련된 내용에 답변하기 위해서는 약관 문서가 필요해요. 약관 문서를 업로드해주세요."
        else:
            answer = self.insurance_rag(question)['result']
            return True, answer
        
    def merge_continuous_message(self, messages):
        merged = list()
        content = list()
        current_role = messages[0]['role']
        for msg in messages:
            if msg['role']==current_role:
                content.append({"text":msg["content"][0]["text"]})
            else:
                merged.append({"role":current_role, "content":content})
                current_role = msg["role"]
                content = [{"text":msg["content"][0]["text"]}]
        merged.append({"role":current_role, "content":content})
        return merged
    
    def init_rag(self, buffer):
        reader = PdfReader(buffer)
        pages = reader.pages
        text = ''
        for page in pages:
            page_content = page.extract_text()
            text += page_content
        
        messages = [
            SystemMessagePromptTemplate.from_template(rag_prompt.format(lang=self.lang)),
            HumanMessagePromptTemplate.from_template('{question}'),
        ]
        qa_prompt = ChatPromptTemplate.from_messages(messages)
        llm = ChatBedrockConverse(
            region_name="ap-northeast-2", model_id='anthropic.claude-3-haiku-20240307-v1:0', temperature=0.
        )
        text_spliiter = RecursiveCharacterTextSplitter(
            chunk_size=4096,
            chunk_overlap=128,
            length_function=len,
            is_separator_regex=False
        )
        docs = text_spliiter.create_documents([text])
        embeddings = BedrockEmbeddings(
            region_name="ap-northeast-2", model_id='amazon.titan-embed-text-v2:0'
        )
        db = FAISS.from_documents(docs, embeddings)
        self.insurance_rag = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type='stuff',
            retriever=db.as_retriever(
                search_kwargs={'k':3},
            ),
            chain_type_kwargs={
                "prompt":qa_prompt
            }
        )