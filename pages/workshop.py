import streamlit as st
import pickle
import openai
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# Page configuration
st.set_page_config(page_title="Build Your Own Productivity Tool", layout="wide")


# Initialize embedding model
@st.cache_resource
def init_embedding_model():
    return HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')


# Load vector store with caching
@st.cache_resource
def load_vectorstore():
    try:
        with open("../workshop_vectorstore.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        st.error("Knowledge base not found. Please process PDFs first.")
        return None


# Function to Summarize with AI
def summarize_with_ai(text):
    if not openai.api_key:
        return "No API key provided. Please enter your OpenAI API key."

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant summarizing workshop knowledge for a user. Keep responses clear, concise, and informative."},
                {"role": "user", "content": f"Summarize this information in simple terms:\n{text}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"


# Initialize session state
if 'embedding_model' not in st.session_state:
    st.session_state.embedding_model = init_embedding_model()

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = load_vectorstore()

# Sidebar for workshop selection
st.sidebar.title("Workshop Topics")
video_selection = st.sidebar.radio("Select a Workshop", [
    "Build a Subscription Dashboard",
    "Automate Task Management",
    "Create a Travel Organizer"
])

# Main title
st.title("Build Your Own Productivity Tool")

# Video Embedding
video_links = {
    "Build a Subscription Dashboard": "https://www.youtube.com/embed/yLu0XwcqnP4",
    "Automate Task Management": "https://www.youtube.com/embed/FRjEQqB7yao",
    "Create a Travel Organizer": "https://www.youtube.com/embed/wccTTW3qfW8"
}

# Displaying the video with proper width and height controls
st.markdown(f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0;">
        <iframe 
            src="{video_links[video_selection]}"
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            frameborder="0" 
            allowfullscreen>
        </iframe>
    </div>
""", unsafe_allow_html=True)

# Sidebar for API key input
st.sidebar.title("API Settings")
user_api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

# API key management
if user_api_key:
    st.session_state['api_key'] = user_api_key
elif 'OPENAI_API_KEY' in st.secrets:
    st.session_state['api_key'] = st.secrets['OPENAI_API_KEY']

openai.api_key = st.session_state.get('api_key')

if not openai.api_key:
    st.warning("Please enter your OpenAI API key to use the chatbot.")
# After your video embed code but before the question input
st.markdown("""
    <script src="https://static.elfsight.com/platform/platform.js" async></script>
    <div class="elfsight-app-094aef79-ae3d-4e33-bbac-e8950bde7316" data-elfsight-app-lazy></div>
""", unsafe_allow_html=True)


# User query input
st.subheader("Ask a Question About This Workshop")
user_query = st.text_input("Ask about this specific workshop:")

# Process query and generate response
if user_query and st.session_state.vectorstore and openai.api_key:
    with st.spinner("Searching and generating response..."):
        try:
            # Search with workshop filter
            docs = st.session_state.vectorstore.similarity_search(
                user_query,
                k=2,
                filter={"workshop_name": video_selection}
            )

            if docs:
                # Combine relevant passages
                raw_text = " ".join([doc.page_content for doc in docs])

                # Create context-aware prompt
                prompt = f"The following information is from the workshop '{video_selection}':\n{raw_text}\n\nUser question: {user_query}"

                # Get AI response
                ai_response = summarize_with_ai(prompt)

                # Display response
                st.write("**Chatbot Response:**")
                st.write(ai_response)

                # Show sources
                with st.expander("View source passages"):
                    for i, doc in enumerate(docs, 1):
                        st.markdown(f"**Source {i}:**")
                        st.write(doc.page_content)
                        st.caption(f"From: {doc.metadata['workshop_name']} | Chunk: {doc.metadata['chunk_index']}")
            else:
                st.info("No relevant information found for this question in the current workshop.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")