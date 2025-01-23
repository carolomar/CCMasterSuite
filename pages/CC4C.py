import requests
import streamlit as st
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile
import os, time

st.title("Leonardo.ai Batch Image Generator")

Leonardo_ai_API = st.text_input("Enter Leonardo API Key", type="password")

st.sidebar.title("Instructions")
st.sidebar.markdown("""
- Enter Leonardo API key
- Add prompts (separate with ====)
- Click Generate Images
- Download individually or as ZIP
""")


def create_image(prompt, api_key):
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
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating image: {str(e)}")
        return None


def get_images(generation_id, api_key):
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting images: {str(e)}")
        return None


prompts = st.text_area(
    "Enter prompts (separate with ====)",
    height=200,
    placeholder="Prompt 1\n====\nPrompt 2\n====\nPrompt 3"
)

if st.button("Generate Images") and Leonardo_ai_API:
    prompt_list = [p.strip() for p in prompts.split('====') if p.strip()]
    total_prompts = len(prompt_list)

    generated_images = []
    failed_prompts = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, prompt in enumerate(prompt_list):
        status_text.write(f"Processing prompt {idx + 1}/{total_prompts}: {prompt[:50]}...")

        result = create_image(prompt, Leonardo_ai_API)
        if not result:
            failed_prompts.append(prompt)
            continue

        generation_id = result['sdGenerationJob']['generationId']

        # Wait for completion with timeout
        start_time = time.time()
        success = False

        while time.time() - start_time < 60:  # 60 second timeout
            status = get_images(generation_id, Leonardo_ai_API)
            if status and status['generations_by_pk']['status'] == 'COMPLETE':
                for img in status['generations_by_pk']['generated_images']:
                    try:
                        img_data = BytesIO(requests.get(img['url']).content)
                        generated_images.append((img_data, prompt))
                        success = True
                    except:
                        continue
                break
            time.sleep(2)

        if not success:
            failed_prompts.append(prompt)

        progress_bar.progress((idx + 1) / total_prompts)

    status_text.write("✅ Processing complete!")

    if failed_prompts:
        st.warning(f"Failed to process {len(failed_prompts)} prompts")

    if generated_images:
        st.subheader(f"Generated Images ({len(generated_images)} total)")

        # Display images in grid
        cols = st.columns(3)
        for idx, (img_data, prompt) in enumerate(generated_images):
            col = cols[idx % 3]
            with col:
                st.image(img_data, caption=f"Prompt: {prompt[:30]}...", width=200)

        # Create ZIP file
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            for idx, (img_data, prompt) in enumerate(generated_images):
                zip_file.writestr(f"image_{idx + 1}.png", img_data.getvalue())

        zip_buffer.seek(0)
        st.download_button(
            label="Download All Images (ZIP)",
            data=zip_buffer,
            file_name=f"leonardo_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )