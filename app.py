from flask import Flask, render_template, make_response, request, send_file
from flask_cors import CORS, cross_origin
from flaskext.mysql import MySQL
import json
import os
import sys
import recommender
import pandas as pd
import scheduler

mysql = MySQL()

rec_engine = recommender.engine

app = Flask(__name__)
cors = CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'vitube'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql.init_app(app)

def response_json(data):
    return make_response(json.dumps(data))

def get_int(val, df=10):
    if not val:
        return df

    if isinstance(val, int):
        return val
    
    if val.isdigit():
        return int(val)

    return df

@app.route("/")
def index():
    return response_json("Video recommender")

@app.route("/recommend-by-video/<video_id>")
def recommend_for_video(video_id):
    length = get_int(request.args.get("limit"))
    length = min(length, 100)
    vid_id = get_int(video_id, None)
    if not vid_id:
        return response_json({"msg": f"Invalid video id: {video_id}"})

    videos = recommender.recommend_for_video(vid_id, length)

    return response_json(videos)


@app.route("/recommend-by-user/<user_id>")
def recommend_for_user(user_id):
    rec_engine.connect(mysql)
    uid = get_int(user_id, None)

    if not uid:
        return response_json({"msg": f"Invalid user id: {user_id}"})

    videos = recommender.recommend_for_user(uid)

    return response_json(videos)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    scheduler.start_scheduler()
    debug = True
    if not debug:
        app.run(threaded=True, host='0.0.0.0', port=port)
    else:
        app.run(debug=True, threaded=True)