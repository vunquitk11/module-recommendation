from flask import Flask, render_template, make_response, request, send_file
from flask_cors import CORS, cross_origin
from flaskext.mysql import MySQL
import json
import os
import sys
import recommender
import pandas as pd

mysql = MySQL()

app = Flask(__name__)
cors = CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'vitube'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql.init_app(app)

def response_json(key, val):
    return make_response(json.dumps({
        key: val
    }))

@app.route("/")
def index():
    return response_json('msg', 1)

@app.route("/recommend-by-video/<video_id>")
def recommend_for_video(video_id=-1):
    if video_id == -1:
        return response_json("msg", "Please provide video id")

    videos = recommender.recommend_for_video(video_id, cursor)

    return response_json(videos)


@app.route("/recommend-by-user/<user_id>")
def recommend_for_user(user_id=-1):
    if user_id == -1:
        return response_json("msg", "Please provide video id")

    videos = recommender.recommend_for_user(user_id, cursor)

    return response_json(videos)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = True
    if not debug:
        app.run(threaded=True, host='0.0.0.0', port=port)
    else:
        app.run(debug=True, threaded=True)