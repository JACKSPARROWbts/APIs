import speech_recognition as sr 
import os 
import requests
from bs4 import BeautifulSoup as bs
from pydub import AudioSegment
from pydub.silence import split_on_silence
from flask import * 
from werkzeug.utils import secure_filename
import json,jwt,datetime
from functools import wraps
from highlighter import *
from googletrans import Translator

app=Flask(__name__)
app.config['SECRET_KEY']='#PULSE'
#app.config['MAX_CONTENT_LENGTH'] = 7 * 1000 * 1000
def get_large_audio_transcription(path):
    r=sr.Recognizer()
    sound = AudioSegment.from_wav(path)  
    chunks = split_on_silence(sound,
        min_silence_len = 700,
        silence_thresh = sound.dBFS-14,
        keep_silence=700,
    )
    folder_name = "audio-chunks"
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    whole_text = ""
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            try:
                text = r.recognize_google(audio_listened)
            except sr.UnknownValueError as e:
                print("Error:", str(e))
            else:
                text = f"{text.capitalize()}. "
                whole_text += text
    # for root,dirs,files in os.walk(os.path.join(os.getcwd(),"audio-chunks")):
    #     for f in files:
    #         os.unlink(os.path.join(root,f))
    return whole_text
def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token=request.args.get('token')
        if not token:
            return jsonify({'message':'Token is missing'}),403
        try:
            data=jwt.decode(token,app.config['SECRET_KEY'])
        except:
            return jsonify({'message':'Token is invalid !!!'}),401
        return f(*args,**kwargs)
    return decorated
@app.route("/login",methods=["GET"])
def login():
    auth=request.authorization
    token=jwt.encode({'user':auth.username,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=30)},app.config['SECRET_KEY'])
    jwtToken={'token':token.decode('UTF-8')}
    return json.dumps(jwtToken)
@app.route('/',methods=['GET'])
def homepage():
    return "<h2> Welcome to the Speech To Text Api created by #PULSE"
@app.route('/attConversion',methods=["POST"])
def audioConversion():
    try:
        length=request.content_length
        contenttype=request.content_type
        data=get_large_audio_transcription(request.files['audio'])
        dataset={'length':length,'contentType':contenttype,'data':data}
        json_dump=json.dumps(dataset)
        return json_dump,200
    except Exception as e:
        return json.dumps({"error":str(e)}),400
@app.route("/currencyConversion",methods=["POST"])
def convert_currency_xe():
    src=request.args.get("src")
    dst=request.args.get("dst")
    amount=request.args.get("amount")
    try:
        def get_digits(text):
            new_text = ""
            for c in text:
                if c.isdigit() or c == ".":
                    new_text += c
            return float(new_text)
    
        url = f"https://www.xe.com/currencyconverter/convert/?Amount={amount}&From={src}&To={dst}"
        content = requests.get(url).content
        soup = bs(content, "html.parser")
        exchange_rate_html = soup.find_all("p")[2]
        last_updated_date=str(exchange_rate_html.parent.parent.find_all("div")[2].text)
        dateTime=last_updated_date[last_updated_date.find("Last updated")+12:]
        json_dump=json.dumps({"updatedDateTime":dateTime,"currencyValue":get_digits(exchange_rate_html.text)})
        return  json_dump
    except Exception as e:
        return json.dumps({"error":"Invalid Currency Passed"+''+str(e)}),400
@app.route("/pdfHighlighter",methods=["GET","POST"])
@token_required
def pdfHighlighter():
    if request.method=="GET":
        return json.dumps({"searchStr":"Enter the string you need to highlight","action":"Enter the type of Highlighting,Methods currently available are Redact, Frame, Highlight, Squiggly, Underline, Strikeout"}),400
    elif request.method=="POST":
        try:
            searchStr=request.args.get("searchStr")
            action=request.args.get("action")
            f=request.files['pdfFile']
            filePath=os.path.join(app.root_path, 'pdfFiles', secure_filename("saved.pdf"))
            #filePath1=os.path.join(app.root_path, 'pdfFiles', secure_filename("removed.pdf"))
            filePath2=os.path.join(app.root_path, 'pdfFiles', secure_filename("highlighted.pdf"))
            f.save(filePath)
            extract_info(input_file=filePath)
            # process_file(
            #             input_file=filePath, output_file=filePath1, 
            #         search_str="searchStr", 
            #         action="Remove"
            #     )
            process_file(
                        input_file=filePath, output_file=filePath2, 
                    search_str=searchStr, 
                    action=action
                )
            return send_file(filePath2,download_name=f.filename),200
        except Exception as e:
            return json.dumps({"error":str(e)}),400
    else:
        return json.dumps({"error":"Invalid request made"})

@app.route("/languageTranslator",methods=["POST"])
def languageTranslator():
    if request.method=="POST":
        try:
            translator=Translator()
            content=request.json
            sentences =content["sentences"]
            dest=content["dest"]
            translations = translator.translate(sentences, dest=dest)
            d=[]
            for translation in translations:
                d.append({"src":translation.src,"translateFrom":translation.origin,"dest":translation.dest,"translateTo":translation.text})
            return json.dumps({"data":d}),200
        except Exception as e:
            return json.dumps({"error":str(e)}),400
    else:
        return json.dumps({"title":"Required parameters to translate the language"})
if __name__=='__main__':
    app.run(port=4444)