import boto3
import json
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain.vectorstores import OpenSearchVectorSearch
from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from cqds import opensearch
from script import bedrock_prompt_dict

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
        },
        {
            "toolSpec": {
                "name": "text_input",
                "description": "전 세계의 여행지, 식당, 랜드마크, 전시품이나 조각상 등에 대해 물으면 답변합니다.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "사용자가 궁금해하는 여행지, 식당, 랜드마크, 전시품이나 조각상 등의 이름입니다."
                            }
                        },
                        "required": [
                            "query"
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
        opensearch_index='hackathon-2024-insurance',
        bedrock_prompt_dict=bedrock_prompt_dict,
        tool_config=tool_config,
        insurance_rag=None,
    ):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        self.model_id = model_id
        self.bedrock_prompt_dict = bedrock_prompt_dict[lang]
        self.tool_config = tool_config
        self.insurance_rag = insurance_rag
        self.lang = lang
        self.opensearch_index = opensearch_index
        
    def get_answer(self, messages):
        messages = [{'role':msg['role'], 'content':[{"text":msg['content']}]} for msg in messages]
        messages = self.merge_continuous_message(messages)
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.bedrock_prompt_dict['agent_system_prompt']}],
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
            system=[{"text":self.bedrock_prompt_dict['summarize_translate_prompt']}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,   
            }
        )
        return response['output']['message']['content'][0]['text']
    
    def get_review_summary(self, reviews):
        text = '\n\n'.join(reviews)
        if len(text):
            messages =  [{"role": "user", "content": [{"text":text}]}]
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                system=[{"text":self.bedrock_prompt_dict['review_summarize_translate_prompt']}],
                messages=messages,
                inferenceConfig={
                    "maxTokens": 4096,   
                }
            )
            return response['output']['message']['content'][0]['text']
        else:
            return None
    
    def get_image_title_result(self, image_titles):
        messages =  [{"role": "user", "content": [{"text":'\n'.join(image_titles)}]}]
        response = self.bedrock_client.converse(
            modelId=self.model_id,
            system=[{"text":self.bedrock_prompt_dict['infer_system_prompt']}],
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
            SystemMessagePromptTemplate.from_template(self.bedrock_prompt_dict['rag_prompt']),
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
        
        # opensearch 초기화
        opensearch_client = opensearch.OpenSearch('alpha')
        if self.opensearch_index in opensearch_client.get_indices:
            opensearch_client.delete_index(index=self.opensearch_index)
        opensearch_client.create_index(index=self.opensearch_index, dimension=1024)
        vector_store = OpenSearchVectorSearch(
            index_name=self.opensearch_index,
            embedding_function=embeddings,
            opensearch_url="https://vpc-vector-alpha-pddgzw24ptgynagltqhdkplu2e.ap-northeast-2.es.amazonaws.com:443",
            vector_field="vector"
        )
        db = vector_store.from_documents(
            docs,
            opensearch_url="https://vpc-vector-alpha-pddgzw24ptgynagltqhdkplu2e.ap-northeast-2.es.amazonaws.com:443",
            embedding=embeddings
        )
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