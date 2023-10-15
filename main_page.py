import streamlit as st
import pandas as pd
from pytube import YouTube
from st_clickable_images import clickable_images
import os
import requests
from time import sleep

upload_endpoint = "https://api.assemblyai.com/v2/upload"
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": st.secrets["auth_key"],   
    "content-type": "application/json"
}

@st.cache_data
def save_audio(url):
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download()
    base, ext = os.path.splitext(out_file)
    file_name = base + '.mp3'
    os.rename(out_file, file_name)
    video_title = yt.title
    return yt.title, file_name, yt.thumbnail_url

@st.cache_data
def upload_to_AssemblyAI(save_location):
    CHUNK_SIZE = 5242880
    
    def read_file(filename):
        with open(filename, 'rb') as _file:
            while True:
                print("chunk uploaded")
                data = _file.read(CHUNK_SIZE)
                if not data:
                    break
                yield data
    upload_response = requests.post(
        upload_endpoint,
        headers=headers, data=read_file(save_location)
    )
    print(upload_response.json())
    #st.write(upload_response.json())
    
    audio_url = upload_response.json()['upload_url']
    print("Uploaded to ", audio_url)
    return audio_url

@st.cache_data
def start_analysis(audio_url):
    
    ## Start transcription job of audio file
    data = {
        'audio_url': audio_url,
        'iab_categories': True,
        'content_safety': True,
        "summarization": True,
        "summary_model": "informative",
        "summary_type": 'bullets'
    }
    
    transcript_response = requests.post(transcript_endpoint, json=data, headers=headers)
    print(transcript_response)
    # st.write(transcript_response.json())
    
    transcript_id = transcript_response.json()['id']
    polling_endpoint = transcript_endpoint + "/" + transcript_id
    print("Transcribing at ", polling_endpoint)
    return polling_endpoint

@st.cache_data
def get_analysis_results(polling_endpoint):
    status = 'submitted'
    while True:
        print(status)
        polling_response = requests.get(polling_endpoint, headers=headers)
        status = polling_response.json()['status']
        st.write(status)
        
        if status == 'submitted' or status == 'processing':
            print('not ready yet')
            sleep(10)
        elif status == 'completed':
            print('creating transcript')
            
            return polling_response # chapters, content_moderation, topic_labels
            break
        else:
            print('error')
            return False

st.title("YouTube Content Analyzer")
st.markdown("With this app you can audit a Youtube channel to get the summary and main topics of it. All you have to do is to input the video link or to pass a list of links. Once you select a video by clicking its thumbnail, you can view:")
st.markdown("1. a summary of the video,")
st.markdown("2. the topics that are discussed in the video,")
st.markdown("3. whether there are any sensitive topics discussed in the video.")

st.header("Input the video link or upload a text file.", divider='rainbow')
st.markdown("Note: Make sure your links are in the format: https://www.youtube.com/watch?v=Mmt****0")
# Input URL
st.subheader("Method 1: Input the video link")
input_url = None
with st.form(key='url_input_text'):
	input_url = st.text_input(label='Video Link')
	submit_button = st.form_submit_button(label='Submit')


st.subheader("Method 2: Upload a text file of video link")
default_bool = st.checkbox('Use default example file', )
if default_bool:
    file = open('./links.txt')
else:
    file = st.file_uploader("Upload a file that includes the links (.txt)")

if len(input_url) > 10 or file is not None:
    st.header("Processing...", divider='rainbow')
    st.write("Please be patient for downloading the audio file ...")
    if file is None: # input url
        url_list = [input_url]
    else: # upload text file
        dataframe = pd.read_csv(file, header=None)
        dataframe.columns = ['urls']
        url_list = dataframe['urls'].tolist()
        #print(url_list) # ['https://www.youtube.com/watch?v=Mmt936kgot0']
        
    titles = []
    locations = []
    thumbnails = []
    
    for video_url in url_list:
        # download audio
        video_title, save_location, video_thumbnail = save_audio(video_url)
        titles.append(video_title)
        locations.append(save_location)
        thumbnails.append(video_thumbnail)
    
    st.write(titles)
    
    selected_video = clickable_images(thumbnails,
                                      titles = titles,
                                      div_style={"height": "400px", "display": "flex", "justify-content": "center", "flex-wrap": "wrap", "overflow-y": 'auto'},
                                      img_style={"margin": "5px", "height": "150px"})
    st.markdown(f"Thumbnail #{selected_video} clicked" if selected_video > -1 else "No image clicked")
    
    if selected_video > -1:
        video_url = url_list[selected_video]
        video_title = titles[selected_video]
        save_location = locations[selected_video]
        
        st.header(video_title, divider='rainbow')
        st.audio(save_location)
        
        # upload mp3 file to AssembleAI
        audio_url = upload_to_AssemblyAI(save_location)
        
        # Start analysis of the file
        polling_endpoint = start_analysis(audio_url)
        
        # receive the results
        results = get_analysis_results(polling_endpoint)
        
        summary = results.json()['summary']
        topics = results.json()['iab_categories_result']['summary']
        sensitive_topics = results.json()['content_safety_labels']['summary']
        
        st.header('Summary of this video', divider='rainbow')
        st.write(summary)
        
        st.header("Sensitive content", divider='rainbow')
        if sensitive_topics != {}:
            st.subheader("Mention of the following sensitive topics detected.")
            moderation_df = pd.DataFrame(sensitive_topics.items())
            moderation_df.columns = ['topic', 'confidence']
            st.dataframe(moderation_df, use_container_width=True)
        else:
            st.subheader("All clear! No sensitive content detected.")
        
        # Topic dataframe
        st.header("Topics discussed", divider='rainbow')
        topics_df = pd.DataFrame(topics.items())
        topics_df.columns = ['topic', 'confidence']
        topics_df['topic'] = topics_df['topic'].str.split(">")
        expanded_topics = topics_df.topic.apply(pd.Series).add_prefix("topic_level_")
        topics_df = topics_df.join(expanded_topics).drop('topic', axis=1).sort_values(['confidence'], ascending=False)
        st.dataframe(topics_df.query('confidence >= 0.85'))