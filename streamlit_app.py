import streamlit as st
from openai import OpenAI
from moviepy.editor import *
import requests
import re
import os
import random
from PIL import Image
from io import BytesIO
import numpy as np

# Set your OpenAI API key
client = OpenAI(api_key=st.secrets.get("OPENAI_KEY", ""))
# Removed global session_id
# session_id = str(random.randint(0,999999999))

def generate_script(prompt):
    script_prompt = f"""
Create a facts-based informational video text script (10 sentences) about the following topic:
{prompt}

Additional requirements:
- Do not add any formatting of the text script, just the plain informational video script.
- EACH sentence uses specific information, facts, and dates.
- Don't use any line prefix or any other meta information - just the informational video text.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a YouTube documentation script-writer."
            },
            {
                "role": "user",
                "content": script_prompt
            }
        ],
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    script = response.choices[0].message.content
    return script

def generate_images(user_prompt, script, video_size):
    paragraphs = [p for p in re.split('\. |\n', script) if p.strip() != '']
    image_urls = []
    for i, para in enumerate(paragraphs):

        image_prompt = f"{para.strip()}"
        image_prompt = ("a photograph representing the following topic: "
                        + user_prompt + "\n\nYou can get some additional inspiration from here: " 
                        + image_prompt + "\n\n IMPORTANT: DON'T ADD ANY TEXT IN THE IMAGE!!!!")
        
        # Create image prompt
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional designer."
                },
                {
                    "role": "user",
                    "content": f'Create a short image prompt creating a visually appealing, beautiful photograph that delivers the core idea of the following paragraph - but make sure to REMOVE any visual element that may contain text: {image_prompt}'
                }
            ],
            temperature=0.6,
            max_tokens=300,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        image_prompt = response.choices[0].message.content
        
        st.write(f"🖼️ Generating image for paragraph {i+1}/{len(paragraphs)}...")

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                n=1,
                quality="standard",
                size=video_size
            )
            image_url = response.data[0].url
            image_urls.append(image_url)
        except Exception as e:
            st.error(f"Skipped one image due to content policy violation - proceeding with one image less")
            continue
                
    return image_urls

def create_voiceover(script, speaker_voice):
    filename = f"voiceover_{st.session_state.session_id}.mp3"
    response = client.audio.speech.create(
        model="tts-1",
        voice=speaker_voice,
        input=script
    )
    response.stream_to_file(filename)
    return filename

def create_video(image_urls, audio_filename):
    audio_clip = AudioFileClip(audio_filename)
    total_duration = audio_clip.duration
    num_images = len(image_urls)
    duration_per_image = total_duration / num_images
    clips = []
    for image_url in image_urls:
        # Download image data
        response = requests.get(image_url)
        image_data = response.content
        # Load image data into PIL Image
        pil_image = Image.open(BytesIO(image_data))
        # Create ImageClip from PIL Image
        image_clip = ImageClip(np.array(pil_image)).set_duration(duration_per_image)
        clips.append(image_clip)
    video_clip = concatenate_videoclips(clips, method='compose')
    video_clip = video_clip.set_audio(audio_clip)
    video_filename = f"output_video_{st.session_state.session_id}.mp4"
    video_clip.write_videofile(
        video_filename,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        temp_audiofile=f'temp-audio_{st.session_state.session_id}.m4a',
        remove_temp=True
    )
    return video_filename

def update_prompt(new_prompt):
    st.session_state.user_prompt = new_prompt

def main():
    st.title("🎥 The Only 100% Free AI Video Creator - No Signup, No Redirects, No Fees!")

    # Initialize session state variables
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ''
        
    # Generate a unique session_id per user session
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(random.randint(0, 999999999))
        
    # Sample prompts
    sample_prompts = [
        'how to make your spouse fall in love with you?',
        'Which herbs are good for women and skin?',
        "The wonders of the deep sea",
        "The impact of climate change on polar bears",
        "A day in the life of a honeybee",
        "Exploring the solar system's planets",
        "The evolution of smartphones",
        "Benefits of mindfulness meditation",
        "The process of photosynthesis",
        "How renewable energy works",
        "The cultural significance of sushi in Japan"
    ]
    
    # User input
    user_prompt = st.text_input(
        "**🎨 What's your video topic?**",
        value=st.session_state.user_prompt,
        key='user_prompt'
    )

    # Expandable section for sample prompts
    with st.expander("Need inspiration? Click on a sample topic below:"):
        cols = st.columns(2)
        for i, prompt in enumerate(sample_prompts):
            cols[i % 2].button(prompt, on_click=update_prompt, args=(prompt,), key=f"prompt_button_{i}")

    # Video size options with display names and corresponding actual sizes
    video_size_options = {
        "📱 Mobile (Instagram 1024x1792)": "1024x1792",
        "🖥️ Desktop (YouTube 1792x1024)": "1792x1024",
        "🔲 Square (Flexible 1024x1024)": "1024x1024",
    }

    # Create a list of display names for the selectbox
    video_size_display_names = list(video_size_options.keys())

    # Use the display names in the selectbox
    selected_size_display_name = st.selectbox("Select video size:", video_size_display_names, index=0)

    # Get the actual video size value
    selected_video_size = video_size_options[selected_size_display_name]

    # Speaker voice options with display names and corresponding API values
    speaker_voice_options = {
        "👩‍💻 Scarlett 'Her' female voice": "shimmer",
        "👧 Young clear female voice": "nova",
        "☀️ Warm female voice": "alloy",
        "🌊 Deep female voice": "echo",
        "📖 Narrator female voice": "fable",
        "🧸 Teddy bear male voice": "onyx"
    }

    # Create a list of display names for the selectbox
    speaker_voice_display_names = list(speaker_voice_options.keys())

    # Use the display names in the selectbox
    selected_voice_display_name = st.selectbox("Select speaker voice:", speaker_voice_display_names, index=0)

    # Get the API voice value corresponding to the selected display name
    selected_speaker_voice = speaker_voice_options[selected_voice_display_name]

    # Style the 'Generate Video' button
    st.markdown("""
        <style>
        /* Style for the 'Generate Video' button */
        div.stButton > button {
            font-size: 24px !important;
            padding: 20px;
            font-weight: bold;
            color: white !important;
            background: linear-gradient(90deg, #ff8a00, #e52e71);
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.5s, transform 0.2s;
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.2);
        }
        div.stButton > button:hover {
            background: linear-gradient(90deg, #e52e71, #ff8a00);
            transform: scale(1.05);
            color: white !important;
        }
        div.stButton > button:active, div.stButton > button:focus {
            background: linear-gradient(90deg, #e52e71, #ff8a00);
            color: white !important;
            outline: none;
        }
        /* Reset styles for buttons inside the expander (sample prompts) */
        div.stExpander div.stButton > button {
            font-size: 14px !important;
            padding: 8px 16px;
            font-weight: normal;
            color: black;
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: none;
            transition: none;
        }
        div.stExpander div.stButton > button:hover {
            background: #e0e0e0;
            color: black;
            transform: none;
        }
        </style>
        """, unsafe_allow_html=True)

    if st.button("Generate Video"):
        # Step 1
        st.write("✍️ Generating script...")
        script = generate_script(user_prompt)

        # Step 2
        st.write("🖼️ Generating images...")

        # Affiliate Link Placement
        aff_link = 'https://koala.sh/?via=finxter'
        st.markdown(
            f'💡 **Business Idea:** While you wait, why not put the '
            f'<a href="{aff_link}" target="_blank">best blogging AI</a> '
            f'(opens safely in new tab) to work to generate a blog article about "{user_prompt}"? '
            f'Use code "VIDEO" for 15% off (lifetime)',
            unsafe_allow_html=True
        )

        # Create Images
        image_urls = generate_images(user_prompt, script, selected_video_size)

        # Check if at least one image was generated
        if not image_urls:
            st.error("No images were generated. Cannot create video.")
            return
        
        # Step 3
        st.write("🎤 Creating voiceover...")
        audio_filename = create_voiceover(script, selected_speaker_voice)

        # Step 4
        st.write("🎬 Creating video...")
        video_filename = create_video(image_urls, audio_filename)

        # Display video
        st.video(video_filename)

        # Indicate completion
        st.success("✅ Video generation complete!")
        st.markdown(
            f'💡 This video will look even better embedded in a blog post! '
            f'Check out the <a href="{aff_link}" target="_blank">best blogging AI</a> '
            f'with code "VIDEO" for 15% off (lifetime)',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
