import streamlit as st
from google.cloud import storage
import tempfile
import pdfplumber
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.oauth2 import service_account
from google.cloud import storage
import json

load_dotenv()

def create_service_account_file():
    service_account_info = {
        "type": "service_account",
        "project_id": st.secrets["connections"]["gcs"]["project_id"],
        "private_key_id": st.secrets["connections"]["gcs"]["private_key_id"],
        "private_key": st.secrets["connections"]["gcs"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["connections"]["gcs"]["client_email"],
        "client_id": st.secrets["connections"]["gcs"]["client_id"],
        "auth_uri": st.secrets["connections"]["gcs"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gcs"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gcs"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gcs"]["client_x509_cert_url"],
        "universe_domain": "googleapis.com"

    }

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(service_account_info, temp)
        temp.flush()
        return temp.name
    

path_to_credentials = create_service_account_file()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path_to_credentials

storage_client = storage.Client()

api_key = st.secrets["general"]["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 1000,
}

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config)


st.cache_data()
def extract_pdf_text(gcs_uri):
    bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    with tempfile.NamedTemporaryFile() as temp_pdf:
        blob.download_to_filename(temp_pdf.name)
        with pdfplumber.open(temp_pdf.name) as pdf:
            return " ".join([page.extract_text() for page in pdf.pages if page.extract_text()])


st.title("Public Company Research 🔍")

uploaded_file = st.file_uploader("Upload 10k (PDF)", type=['pdf'])

if uploaded_file is not None:
    bucket = storage_client.get_bucket('company10k')
    blob = bucket.blob(uploaded_file.name)
    blob.upload_from_string(uploaded_file.getvalue(), content_type='application/pdf')
    document_text = extract_pdf_text(f'gs://company10k/{uploaded_file.name}')

    messages = [{'role': 'user', 'parts': [document_text]}]

    st.text_input("What is your question?", key="user_question")
    if st.session_state.user_question:
        
        messages.append({'role': 'user', 'parts': [st.session_state.user_question]})
        response = model.generate_content(messages)
        st.write(response.text)
        messages.append({'role': 'model', 'parts': [response.text]})
    
        st.text_input("Next question?", key="next_question")
        if st.session_state.next_question:
            messages.append({'role': 'user', 'parts': [st.session_state.next_question]})
            response = model.generate_content(messages)
            st.write(response.text)