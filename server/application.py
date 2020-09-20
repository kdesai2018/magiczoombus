import os
import json
#import urllib.request
import urllib.parse as urlparse
from urllib.request import urlopen
from ibm_watson import NaturalLanguageUnderstandingV1, SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, KeywordsOptions, EntitiesOptions
from flask import Flask, render_template, send_file, Response, request, jsonify
from flask_cors import CORS
import xml.etree.ElementTree as ET
from smart_data_fetcher import get_smart_data_for_keyword

app = Flask(__name__, static_url_path='/static', static_folder=os.path.join("../","client","static"))
CORS(app)

UPLOADS_FOLDER = "../temp_files"

@app.route('/', methods=['GET'])
def render_index():
    return send_file(os.path.join("../","client","index.html"))


@app.route('/getinfo', methods=['GET'])
def get_video_info():
    # url contains the url string
    url = request.args['url']
    # url = "https://www.youtube.com/watch?v=O5nskjZ_GoI&list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo&t=0s&ab_channel=CrashCourse"
    
    # Get the video id
    url_data = urlparse.urlparse(url)
    query = urlparse.parse_qs(url_data.query)
    video_id = query["v"][0]

    print('Began getting info')

    # Create URL for transcript
    transcript_url = "http://video.google.com/timedtext?lang=en&v="+video_id
    print(transcript_url)
    #  get transcript xml sheet from transcript_url
    transcript_response = urlopen(transcript_url).read()
    tree = ET.fromstring(transcript_response)

    assert(tree.tag == 'transcript')
    timed_transcript = {}
    keyword_cache = {}

    # print(url)
    print('Just before tree thing')

    for node in tree.iter('text'):
        start_time = round(float(node.attrib['start']))
        try:
            ibm_data = getKeywordsText(node.text, 1)
        except:
            continue
        
        if ibm_data and 'keywords' in ibm_data and len(ibm_data['keywords'])>=1 and ibm_data['keywords'][0]['relevance'] > 0.85:
            print(ibm_data['keywords'])
            keyword = ibm_data['keywords'][0]['text']
            keyword.lower()
        else:
            continue
        
        if keyword in keyword_cache:
            timed_transcript[start_time] = keyword_cache[keyword]
        else:
            google_knowledge = get_smart_data_for_keyword(keyword)
            # print(google_knowledge)
            if google_knowledge:
                # print('Got a word baby')
                timed_transcript[start_time] = google_knowledge
                keyword_cache[keyword] = google_knowledge
        
    print('Done')
    # for key, val in timed_transcript.items():
        # print(str(key) + ':' + str(val))
    return timed_transcript

def getKeywordsURL(transcript_url):
    #IBM Watson NLU
    authenticator = IAMAuthenticator('TWS446L2CH4Zxnrh-nwh3T2g8stRlB08e4iyjAKyBHg0')
    natural_language_understanding = NaturalLanguageUnderstandingV1(
        version='2020-08-01',
        authenticator=authenticator
    )

    natural_language_understanding.set_service_url('https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/816f28bc-9729-48ca-b11a-c736524e6ad6')

    response = natural_language_understanding.analyze(
        url=transcript_url,
        features=Features(keywords=KeywordsOptions(sentiment=False,emotion=False,limit=1), entities=EntitiesOptions(sentiment=False,limit=1))).get_result()
    return response



def getKeywordsText(text, numWords):
    #IBM Watson NLU
    try:
        # print(text)
        response = natural_language_understanding.analyze(
            text=text,
            features=Features(keywords=KeywordsOptions(sentiment=False,emotion=False,limit=numWords), entities=EntitiesOptions(sentiment=True,limit=1))).get_result()
    except:
        response = None
        # print('HOLY SHIT SOMETHING WENT WRONG')
    return response


if __name__ == "__main__":
    authenticator = IAMAuthenticator('TWS446L2CH4Zxnrh-nwh3T2g8stRlB08e4iyjAKyBHg0')
    natural_language_understanding = NaturalLanguageUnderstandingV1(
        version='2020-08-01',
        authenticator=authenticator
    )
    natural_language_understanding.set_service_url('https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/816f28bc-9729-48ca-b11a-c736524e6ad6')
    app.run()
    # print(smart_data_fetcher.get_smart_data_for_keyword('elephant'))

@app.route('/getuploadedinfo', methods=['POST'])
def get_uploaded_video_info():
    #request.files["video"] = f
    if "video" not in request.files:
        return None
    video_file = request.files["video"]
    #video_file = f
    save_location = os.path.join(UPLOADS_FOLDER, video_file.filename)
    video_file.save(save_location)
    # Convert the mp4 to an mp3
    mp3_filename = save_location.replace(".mp4", ".mp3")
    os.system("ffmpeg -y -i " + save_location + " " + mp3_filename)
    transcript = getTranscriptForUploadedAudio(mp3_filename)
    os.remove(save_location)
    os.remove(mp3_filename)
    return "goodbye"

# mp3File must come in BinaryIO format for easy upload to STT API
def getTranscriptForUploadedAudio(mp3File):
    authenticator = IAMAuthenticator('JNJkBoGNQKYihv3CPqXMtuKlgAVQcFrunct_mV2Yv4cx')
    STT_service = SpeechToTextV1(authenticator=authenticator)
    STT_service.set_service_url('https://api.us-south.natural-language-understanding.watson.cloud.ibm.com/instances/816f28bc-9729-48ca-b11a-c736524e6ad6')
    with open(os.path.join(os.path.dirname('__file__'), mp3File),  'rb') as audio_file:
        transcript = STT_service.recognize(audio=audio_file, timestamps=True).get_result()
        return transcript

@app.route('/ansh', methods=['GET'])
def get_fake_data():
    # Fake data function for use by the man, the myth, the legend
    fake_dict = {
        4 : {
            "proper_name": "French Revolution",
            "what_is_term": "Event",
            "description": "Period of social and political upheaval in France in 1789-1799"
        },
        9 : {
            "proper_name": "Donuts",
            "what_is_term": "Food",
            "description": "Probably one of the best foods ever made"
        },
        16 : {
            "proper_name": "Xenoblade Chronicles",
            "what_is_term": "Video Game",
            "wikipedia_link": "http://gamebot2.com"
        },
        7200 : {
            "proper_name": "Hyrule Warriors",
            "what_is_term": "Video Game",
            "wikipedia_link": "http://google.com",
            "image_url": "https://www.imore.com/sites/imore.com/files/styles/large/public/field/image/2020/09/hyrule-warriors-age-of-calamity-champions.jpg"
        }
    }

    return jsonify(fake_dict)
