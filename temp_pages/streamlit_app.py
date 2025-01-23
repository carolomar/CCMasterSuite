import streamlit as st
import json

# Set up the sidebar menu
st.sidebar.title("Cazie's Toolbox")
menu_option = st.sidebar.radio("Menu",
                               ["Create Associations", "Business Apps", "Story Making", "Recipes", "Content Creation"])


# Function for downloading files
def download_content(data, filename):
    json_data = json.dumps(data, indent=4)
    st.download_button(
        label="Download as JSON",
        data=json_data,
        file_name=f"{filename}.json",
        mime="application/json",
    )


# Main app logic
if menu_option == "Create Associations":
    st.title("Create Associations")
    st.write("Use memory palace technique to store associations.")

    # Input form for associations
    association = st.text_input("Enter something to associate:")
    if association:
        # You could save this to a file or JSON
        st.write(f"Stored: {association}")
        download_content({"association": association}, "association_data")

elif menu_option == "Business Apps":
    st.title("Business Apps")
    st.write("Get prompts for business solutions.")

    # Input form for business name generation or logo ideas
    business_type = st.text_input("Describe your business:")
    if business_type:
        st.write(f"Generating ideas for: {business_type}")
        # Sample chat model interaction (replace with real API or logic)
        ideas = {"business_name": f"{business_type} Solutions", "logo": "A creative logo idea"}
        st.write(ideas)
        download_content(ideas, "business_ideas")

elif menu_option == "Story Making":
    st.title("Story Making")
    st.write("Create your story.")

    # Input for story-making components
    story_prompt = st.text_input("Enter your story idea or theme:")
    if story_prompt:
        st.write(f"Generating story for: {story_prompt}")
        story = {"title": f"The Tale of {story_prompt}", "plot": "A thrilling adventure awaits!"}
        st.write(story)
        download_content(story, "story")

elif menu_option == "Recipes":
    st.title("Recipes")
    st.write("Generate meal ideas.")

    # Input for recipe creation
    ingredients = st.text_input("Enter ingredients you have:")
    if ingredients:
        st.write(f"Generating recipes with: {ingredients}")
        recipe = {"recipe_name": f"Delicious {ingredients} Stir Fry",
                  "steps": ["Chop ingredients", "Stir fry with spices", "Serve hot"]}
        st.write(recipe)
        download_content(recipe, "recipe")

elif menu_option == "Content Creation":
    st.title("Content Creation")
    st.write("Get ideas for social media content.")

    # Input for content creation ideas
    platform = st.selectbox("Choose platform:", ["YouTube", "TikTok", "Instagram"])
    content_topic = st.text_input(f"What kind of content do you want to create for {platform}?")

    if content_topic:
        st.write(f"Generating content ideas for {platform} on topic: {content_topic}")
        content = {"platform": platform, "idea": f"Create a viral {content_topic} video!"}
        st.write(content)
        download_content(content, "content_creation_ideas")
