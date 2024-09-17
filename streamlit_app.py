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

def generate_script(prompt):
    script_prompt = f"""
Create a facts-based informational video text script (10 sentences) about the following topic:
{prompt}

Additional requirements:
- Do not add any formatting of the text script, just the plain informational video script.
- Write in a visual way so each line can be used as an input for an image generation AI tool.
- Don't use any line prefix or any other meta information - just the informational video text.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a YouTube script-writer."
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
        image_prompt = ("a hyper-realistic photograph representing the following topic: "
                        + user_prompt + "\n\nYou can get some additional inspiration from here: " 
                        + image_prompt + "\n\n IMPORTANT: DON'T ADD ANY TEXT IN THE IMAGE!!!!")
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
    filename = "voiceover.mp3"
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
    video_clip.write_videofile("output_video.mp4", fps=24)

def main():
    st.title("🎥 The Only 100% Free AI Video Creator - No Signup, No Redirects, No Fees!")

    # User input
    user_prompt = st.text_input("**🎨 What's your video topic?**", 
                                "Which herbs are good for women and skin?")

    # Video size options with display names and corresponding actual sizes
    video_size_options = {
        "📱 Mobile (Instagram 1024x1792)": "1024x1792",
        "🖥️ Desktop (YouTube 1792x1024)": "1792x1024",
        "🔲 Square (Flexible 1024x1024)": "1024x1024",
    }

    # Create a list of display names for the selectbox
    video_size_display_names = list(video_size_options.keys())

    # Use the display names in the selectbox
    selected_size_display_name = st.selectbox("Select video size:", video_size_display_names, index=0)  # default to 0

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

    if st.button("Generate Video"):
        # Step 1
        st.write("✍️ Generating script...")
        script = generate_script(user_prompt)

        # Step 2
        st.write("🖼️ Generating images...")

        # Affiliate Link Placement
        aff_link = 'https://koala.sh/?via=finxter'
        st.markdown(f'💡 **Business Idea:** While you wait, why not put the <a href="{aff_link}" target="_blank">best blogging AI</a> (opens safely in new tab) to work to generate a blog article about "{user_prompt}"? Use code "VIDEO" for 15% off (lifetime)',
                   unsafe_allow_html=True)

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
        create_video(image_urls, audio_filename)

        # Display video
        st.video("output_video.mp4")

        # Indicate completion
        st.success("✅ Video generation complete!")
        st.markdown(f'💡 This video will look even better embedded in a blog post! Check out the <a href="{aff_link}" target="_blank">best blogging AI</a> with code "VIDEO" for 15% off (lifetime)',
                   unsafe_allow_html=True)


if __name__ == "__main__":
    main()
