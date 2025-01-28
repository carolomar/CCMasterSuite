import openai
import streamlit as st
import requests
from PIL import Image
from io import BytesIO, StringIO
import csv
from zipfile import ZipFile
import os, time
from datetime import datetime

st.title("....YouTube Content + Image Generator")

# Sidebar instructions
st.sidebar.title("Quick Start")
st.sidebar.markdown("""
- Enter both API keys
- Input video topic, duration, style
- Click 'Generate Content'
- Images generate in batches of 10
- Click 'Generate Next Batch'
- Download images and CSV
""")
st.sidebar.info("💡 CSV works with Canva's bulk import")
st.sidebar.warning("⏳ Full generation takes ~30-45 minutes")

# Detailed instructions
with st.expander("📚 How to Use This App", expanded=False):
    st.markdown("""
    **Step-by-Step Guide:**
    1. **API Keys**
        - OpenAI API key: Script generation
        - Leonardo AI key: Image creation

    2. **Input Details**
        - Topic: Video's main subject
        - Duration: Length in minutes
        - Style: Content tone

    3. **Generation Process**
        - Script generates first
        - Images create in batches
        - Progress tracker included

    4. **Downloads**
        - CSV for Canva import
        - ZIP of all images
        - Image URLs list
    """)

# Initialize session state
if 'current_batch' not in st.session_state:
    st.session_state.current_batch = 0
    st.session_state.all_batches = []
    st.session_state.generated_images = []
    st.session_state.generated_urls = []
    st.session_state.script = None
    st.session_state.image_data = []

# API Keys
openai_api_key = st.text_input("Enter OpenAI API Key:", type="password")
leonardo_api_key = st.text_input("Enter Leonardo API Key:", type="password")


@st.cache_data(ttl=3600)
def generate_script(topic, duration, style):
    prompt = (
        f"You are a professional scriptwriter for YouTube videos. Create a {duration}-minute script using this exact topic title: '{topic}'\n"
        f"Use a normal speaking pace (~750 words/minute). Break into sections with clear headings.\n"
        f"Style: {style}\n"
        f"The first line must be exactly: '{topic}'\n"
        f"Ensure the script flows smoothly, keeping viewers engaged from start to finish."
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    return response.choices[0].message.content


def generate_image_prompts(script):
    prompt = (
        "You are a prompt designer for Leonardo AI. Create contextually relevant image prompts based on the script context.\n"
        "Rules:\n"
        "1. Stay strictly within the subject matter's historical/factual context\n"
        "2. For any mention of 'legend' or similar terms, use actual historical references from the topic\n"
        "3. Maintain cultural and historical accuracy\n"
        "4. Repeat key identifying phrases in each prompt to maintain consistency\n"
        f"Script: {script}\n"
        "Format each prompt to include: setting, lighting, camera angle, style"
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    return response.choices[0].message.content


@st.cache_data(ttl=3600)
def create_image(prompt, api_key):
    blocked_words = ['bondage', 'slave', 'slavery', 'enslaved']
    for word in blocked_words:
        prompt = prompt.lower().replace(word, 'person')

    try:
        url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        payload = {
            "width": 1472,
            "height": 832,
            "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "num_images": 2,
            "prompt": prompt,
            "ultra": False,
            "styleUUID": "111dc692-d470-4eec-b791-3475abac4c46",
            "enhancePrompt": False
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()

        if 'sdGenerationJob' not in result:
            st.error(f"Error: {result.get('error', 'Unknown error')}")
            return None

        return result

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def get_images(generation_id, api_key):
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    response = requests.get(url, headers=headers)
    return response.json()


def save_image_to_memory(url):
    response = requests.get(url)
    return BytesIO(response.content)


def prepare_prompts(script, batch_size=10):
    sections = script.split('\n\n')
    all_prompts = []
    all_prompts.extend([sections[0]] * 2)  # Intro
    for section in sections[1:-1]:
        all_prompts.extend([section] * 5)  # Sections
    all_prompts.extend([sections[-1]] * 2)  # Outro
    return [all_prompts[i:i + batch_size] for i in range(0, len(all_prompts), batch_size)]


def process_generated_images(generated_images, script, start_index=0):
    sections = script.split('\n\n')
    image_data = []
    img_counter = start_index

    total_intro = 2
    total_per_section = 5
    total_outro = 2

    while img_counter < len(generated_images):
        if img_counter < total_intro:
            filename = f"intro_{img_counter + 1}.png"
            section_title = "Intro Section"
        elif img_counter < total_intro + (len(sections) - 2) * total_per_section:
            section_num = (img_counter - total_intro) // total_per_section + 1
            image_num = (img_counter - total_intro) % total_per_section + 1
            filename = f"section_{section_num}_image_{image_num}.png"
            section_title = sections[section_num].split('\n')[0]
        else:
            outro_num = img_counter - (total_intro + (len(sections) - 2) * total_per_section) + 1
            filename = f"outro_{outro_num}.png"
            section_title = "Outro Section"

        img_data = generated_images[img_counter]
        with open(filename, 'wb') as f:
            f.write(img_data.getvalue())
        image_data.append([filename, section_title])
        img_counter += 1

    return image_data


# User Inputs
topic = st.text_input("Enter your video topic:")
duration = st.slider("Select video duration (minutes):", min_value=1, max_value=10, value=5)
style = st.text_area("Describe your style (e.g., Casual, Educational, Humorous) OR add short sample of your writing")

if st.button("Generate Content") or ('script_generated' in st.session_state and st.session_state.script_generated):
    if not openai_api_key or not leonardo_api_key:
        st.error("Please enter both API keys before proceeding.")
    else:
        openai.api_key = openai_api_key

        if st.session_state.script is None:
            with st.spinner("Generating script..."):
                st.session_state.script = generate_script(topic, duration, style)
                st.session_state.all_batches = prepare_prompts(st.session_state.script)
                st.session_state.script_generated = True
            st.subheader("Generated Script")
            st.write(st.session_state.script)

        if st.session_state.current_batch < len(st.session_state.all_batches):
            with st.spinner(
                    f"Generating images (Batch {st.session_state.current_batch + 1}/{len(st.session_state.all_batches)})..."):
                current_prompts = st.session_state.all_batches[st.session_state.current_batch]

                for i, prompt in enumerate(current_prompts):
                    progress_text = st.empty()
                    progress_text.write(f"Processing image {i + 1} of {len(current_prompts)} in current batch...")

                    result = create_image(prompt, leonardo_api_key)
                    if result:
                        generation_id = result['sdGenerationJob']['generationId']

                        for _ in range(30):
                            status = get_images(generation_id, leonardo_api_key)
                            if status['generations_by_pk']['status'] == 'COMPLETE':
                                for img in status['generations_by_pk']['generated_images']:
                                    img_data = save_image_to_memory(img['url'])
                                    st.session_state.generated_images.append(img_data)
                                    st.session_state.generated_urls.append(img['url'])
                                break
                            time.sleep(1)

                new_image_data = process_generated_images(
                    st.session_state.generated_images,
                    st.session_state.script,
                    len(st.session_state.image_data)
                )
                st.session_state.image_data.extend(new_image_data)

                st.session_state.current_batch += 1

                st.write(f"Completed {st.session_state.current_batch} of {len(st.session_state.all_batches)} batches")

                if st.session_state.current_batch < len(st.session_state.all_batches):
                    st.button("Generate Next Batch", key="next_batch")
                else:
                    st.success("All images generated!")

        if st.session_state.generated_images:
            csv_string = StringIO()
            csv.writer(csv_string).writerows([['Image', 'Caption']] + st.session_state.image_data)

            st.download_button(
                label="Download Canva CSV Template",
                data=csv_string.getvalue(),
                file_name="canva_bulk_import.csv",
                mime="text/csv"
            )

            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, "w") as zip_file:
                for filename, _ in st.session_state.image_data:
                    zip_file.write(filename)

            zip_buffer.seek(0)
            st.download_button(
                label="Download All Images",
                data=zip_buffer,
                file_name="images.zip",
                mime="application/zip"
            )

            if st.session_state.generated_urls:
                urls_text = '\n'.join(st.session_state.generated_urls)
                st.download_button(
                    "Download Image URLs",
                    urls_text,
                    file_name="image_urls.txt",
                    mime="text/plain"
                )

            st.subheader("Generated Images")
            cols = st.columns(3)
            for idx, img_data in enumerate(st.session_state.generated_images):
                col = cols[idx % 3]
                with col:
                    st.image(img_data, width=200)

            # Local save option
            save_path = st.text_input("Save directory path (optional):", "")
            if save_path and st.button("Save Files Locally"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_dir = os.path.join(save_path, f"generation_{timestamp}")
                os.makedirs(save_dir, exist_ok=True)

                for idx, img_data in enumerate(st.session_state.generated_images):
                    with open(os.path.join(save_dir, f"image_{idx + 1}.png"), 'wb') as f:
                        f.write(img_data.getvalue())

                with open(os.path.join(save_dir, 'canva_bulk_import.csv'), 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows([['Image', 'Caption']] + st.session_state.image_data)

                st.success(f"Files saved to {save_dir}")

if st.button("Start Over"):
    st.session_state.current_batch = 0
    st.session_state.all_batches = []
    st.session_state.generated_images = []
    st.session_state.generated_urls = []
    st.session_state.script = None
    st.session_state.image_data = []
    st.session_state.script_generated = False
    st.rerun()