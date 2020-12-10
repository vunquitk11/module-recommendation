import os
import pandas as pd
import numpy as np
import scipy
import re
from sklearn.feature_extraction.text import TfidfVectorizer

class Recommender:
    def __init__(self, mysql):
        self.mysql = mysql

    def connect(self):
        connection = self.mysql.connect()
        self.cursor = connection.cursor()

    @staticmethod
    def save_all_vectors(vectors):
        np.save("all_vectors", vectors)

    def load_vectors(self):
        self.vectors = np.load("all_vectors.npy")

    def init_all_dataframe(self):
        self.activity_df = self.build_df("activities", "id,type,user_id,target_id")
        self.history_df = self.build_df(
            "watch_histories",
            "id,user_id,video_id,current_like,current_dislike,current_view"
        )
        self.video_df = self.build_df(
            "videos",
            "id,video_src,thumbnail,name,description,duration,tags"
        )

    def build_df(self, table, columns, condition=""):
        sql = f"SELECT {columns} from {table}"
        if condition:
            sql += f"WHERE ${condition}"

        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        df = pd.DataFrame(data)
        df.columns = columns.split(",")
        return df
    

## Export ##
def recommend_for_video(video_id, cursor):
    
    
    return videos


def recommend_for_user(user_id, cursor):
    
    
    return videos