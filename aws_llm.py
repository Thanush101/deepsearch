import boto3
import json
import streamlit as st

bedrock_claude_3_5 = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    region_name=st.secrets["AWS_REGION"]
)

bedrock_claude_3_7 = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
    region_name="us-west-2"
)


def llm_response(system_prompt, user_prompt):

    ip_cost = (3/1000000)*86.0
    op_cost = (15/1000000)*86.0    

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8000,
        "top_k": 250,
        "stop_sequences": [],
        "temperature": 0.5,
        "top_p": 0.999,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt + "/n/n" + user_prompt 
                    }
                ]
            }
        ]
    }

    try:
        response = bedrock_claude_3_5.invoke_model(
            modelId="apac.anthropic.claude-3-5-sonnet-20241022-v2:0", 
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        response_body = json.loads(response['body'].read())

        cost = ip_cost*response_body['usage']['input_tokens'] + op_cost*response_body['usage']['output_tokens']
        
        return  response_body['content'][0]['text'], cost
        
    except Exception as e:
        return  f"Error: {e}",0



def llm_response_rsng(system_prompt, user_prompt):

    ip_cost = (15/1000000)*86.0
    op_cost = (75/1000000)*86.0

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8000,
        "top_k": 250,
        "stop_sequences": [],
        "temperature": 0.5,
        "top_p": 0.999,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt + "/n/n" + user_prompt 
                    }
                ]
            }
        ]
    }
    
    try:
        # Replace "correct-model-id" with the actual model identifier you intend to use
        response = bedrock_claude_3_7.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        # Parse the response body
        response_body = json.loads(response['body'].read())
        
        cost = ip_cost*response_body['usage']['input_tokens'] + op_cost*response_body['usage']['output_tokens']
        
        return  response_body['content'][0]['text'], cost        

    except Exception as e:
        return f"Error: {e}",0


# if __name__ == "__main__":
#     system_prompt ="Act as a 23"
#     user_prompt ="Provide a JD for digital marketing leader"
#     print(llm_response(system_prompt, user_prompt)[0], "Cost: ", llm_response(system_prompt, user_prompt)[1])
#     print("\n\n\n", llm_response_rsng(system_prompt, user_prompt)[0], "Cost: ", llm_response_rsng(system_prompt, user_prompt)[1])