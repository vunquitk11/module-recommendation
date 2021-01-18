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
    print("Start update data")
    start = datetime.datetime.now()

    engine = recommender.Recommender()
    engine.allow_update()
    engine.connect(app.mysql)
    # engine.load_vectors()
    engine.init_all_dataframe()
    # engine.build_vectors()
    engine.save_all_dataframe()

    print(f"Finished in {datetime.datetime.now() - start}")

#  ================ export ================ #
update_recommender_data()
def start_scheduler():
    set_interval(update_recommender_data, one_minute * 15)
