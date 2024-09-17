import streamlit as st
from openai import OpenAI
from moviepy.editor import *
import requests
import re
import os

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
                "content": [
                    {
                        "type": "text",
                        "text": "You are a YouTube script-writer."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": script_prompt
                    }
                ]
            }
        ],
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={
            "type": "text"
        }
    )
    script = response.choices[0].message.content
    return script

def generate_images(user_prompt, script, video_size):
    paragraphs = [p for p in re.split('\. |\n', script) if p.strip() != '']
    image_paths = []
    for i, para in enumerate(paragraphs):
        image_prompt = f"{para.strip()}"
        image_prompt = ("a hyper-realistic photograph representing the following topic:"
                        + user_prompt + "\n\nYou can get some additional inspiration from here: " 
                        + image_prompt + "\n\n IMPORTANT: DON'T ADD ANY TEXT IN THE IMAGE!!!!")
        st.write(f"Generating image for paragraph {i+1}: {image_prompt}")
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            n=1,
            quality="standard",
            size=video_size
        )
        image_url = response.data[0].url
        image_filename = f"image_{i+1}.jpg"
        image_data = requests.get(image_url).content
        with open(image_filename, 'wb') as handler:
            handler.write(image_data)
        image_paths.append(image_filename)
    return image_paths

def create_voiceover(script, speaker_voice):
    filename = "voiceover.mp3"
    response = client.audio.speech.create(
        model="tts-1",
        voice=speaker_voice,
        input=script
    )
    response.stream_to_file(filename)
    return filename

def create_video(image_paths, audio_filename):
    audio_clip = AudioFileClip(audio_filename)
    total_duration = audio_clip.duration
    num_images = len(image_paths)
    duration_per_image = total_duration / num_images
    clips = []
    for image_path in image_paths:
        image_clip = ImageClip(image_path).set_duration(duration_per_image)
        clips.append(image_clip)
    video_clip = concatenate_videoclips(clips, method='compose')
    video_clip = video_clip.set_audio(audio_clip)
    video_clip.write_videofile("output_video.mp4", fps=24)

def main():
    st.title("AI Video Generator")

    # User input
    user_prompt = st.text_input("Enter your prompt:", "which herbs are good for women and skin?")

    # Video size options with display names and corresponding actual sizes
    video_size_options = {
        "Square (1024x1024)": "1024x1024",
        "Instagram (mobile 1024x1792)": "1024x1792",
        "YouTube (landscape 1792x1024)": "1792x1024"
    }

    # Create a list of display names for the selectbox
    video_size_display_names = list(video_size_options.keys())

    # Use the display names in the selectbox
    selected_size_display_name = st.selectbox("Select video size:", video_size_display_names, index=0)  # default to "Square (1024x1024)"

    # Get the actual video size value
    selected_video_size = video_size_options[selected_size_display_name]

    # Speaker voice options with display names and corresponding API values
    speaker_voice_options = {
        "Scarlett 'Her' female voice": "shimmer",
        "Young clear female voice": "nova",
        "Warm female voice": "alloy",
        "Deep female voice": "echo",
        "Narrator female voice": "fable",
        "Teddy bear male voice": "onyx",
    }

    # Create a list of display names for the selectbox
    speaker_voice_display_names = list(speaker_voice_options.keys())

    # Use the display names in the selectbox
    selected_voice_display_name = st.selectbox("Select speaker voice:", speaker_voice_display_names, index=4)  # default to "Young female voice"

    # Get the API voice value corresponding to the selected display name
    selected_speaker_voice = speaker_voice_options[selected_voice_display_name]

    if st.button("Generate Video"):
        # Step 1
        st.write("Generating script...")
        script = generate_script(user_prompt)
        # st.write("Generated Script:")
        # st.write(script)

        with open("script.txt", "w") as f:
            f.write(script)

        # Step 2
        st.write("Generating images...")
        image_paths = generate_images(user_prompt, script, selected_video_size)

        # Display images
        # for image_path in image_paths:
        #    st.image(image_path)

        # Step 3
        st.write("Creating voiceover...")
        audio_filename = create_voiceover(script, selected_speaker_voice)
        # st.audio(audio_filename)

        # Step 4
        st.write("Creating video...")
        create_video(image_paths, audio_filename)

        # Display video
        st.video("output_video.mp4")

        # Done
        # st.success("Video created: output_video.mp4")

if __name__ == "__main__":
    main()
