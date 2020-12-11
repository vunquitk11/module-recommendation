import recommender
import threading
import requests
import time
import datetime
import app

one_minute = 60


def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t


def update_recommender_data():
    engine = recommender.Recommender()
    # engine.connect(app.mysql)
    engine.load_vectors()
    engine.init_all_dataframe()

    print(engine.recommend_for_vid(24))

#  ================ export ================ #
def start_scheduler():
    return
    set_interval(update_recommender_data, one_minute * 500)
