# Youtube_video_analyzer

# Project Description:

With this app you can audit a Youtube channel to get the summary and main topics of it. All you have to do is to input the video link or to pass a list of links. Once you select a video by clicking its thumbnail, you can view:

1. A summary of the video
2. the topics that are discussed in the video
3. whether there are any sensitive topics discussed in the video

# Project Process

1. Get the Youtube video URL from user input or uploading a text file.

![img](https://github.com/stemgene/Youtube_video_analyzer/blob/main/img/1.png)

2. Get and display the video infomation by `pytube` API

3. Download the audio file of the video which user clicks it.

4. Upload the audio file to AssemblyAI to get summary result

5. Display the summary and topics. The topics should be with at least 85% confidence.

![img](https://github.com/stemgene/Youtube_video_analyzer/blob/main/img/2.png)


