import os
import pandas as pd
import numpy as np
import scipy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
pd.options.mode.chained_assignment = None

tf_vectorizer = TfidfVectorizer(
    min_df=3, max_features=3000,
    strip_accents="unicode", analyzer="word",
    token_pattern=r"\w{3,}",
    ngram_range=(1, 3),
    stop_words="english")

def consine_sim(x1, x2):
    return 1 - scipy.spatial.distance.cosine(x1, x2)


def concat_feat(feats, mat):
    feats.fillna(0, inplace=True)
    vec = feats.values
    combined = np.concatenate([vec, mat.A], axis=1)
    row_max = combined.max(axis=0)
    return combined / row_max[np.newaxis, :]

class Recommender:
    def __init__(self):
        self.save_dir = "./storage"
        self.override = False

    def _p(self, fname):
        return os.path.join(self.save_dir, fname)

    def allow_update(self):
        self.override = True

    def connect(self, mysql):
        connection = mysql.connect()
        self.cursor = connection.cursor()

    def save_vectors(self, vectors):
        np.save(self._p("feature_vectors.npy"), vectors)

    def load_vectors(self):
        self.vectors = np.load(self._p("feature_vectors.npy"))

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

    def save_all_dataframe(self):
        for attr in ["history_df", "activity_df", "video_df"]:
            getattr(self, attr).to_csv(self._p(attr + ".csv"))

    def build_df(self, table, columns, condition=""):
        fpath = self._p(table + ".csv")
        if not self.override and os.path.isfile(fpath):
            return pd.read_csv(fpath)

        sql = f"SELECT {columns} from {table}"
        if condition:
            sql += f"WHERE ${condition}"

        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        df = pd.DataFrame(data)
        df.columns = columns.split(",")
        return df

    def build_vectors(self):
        return

        self.init_all_dataframe()
        # Fill NaN values by empty string
        self.video_df["description"].fillna("", inplace=True)
        # Remove all URL in description, it's unnessessary
        self.video_df["description"] = self.video_df["description"].apply(lambda x: re.sub(r"http\S+", "", x or ""))

        # Features used to calculate similiarity between 2 videos
        features = ["id", "duration", "category_id", "comments", "name", "description"]

        vid_info = self.video_df[features]
        # Replace "id" by "video_id"
        vid_info.columns = ["video_id"] + features[1:]

        # Join the videoinfo with history
        self.history_df = self.history_df.merge(vid_info, on="video_id", how="left")

        # All features
        useful_feats = [
            "likes", "dislikes", "views", "duration",
            "category_id", "comments", "name", "description",
        ]

        feats = self.video_df[useful_feats]
        feats["text"] = feats["description"] + " " + feats["name"]
        feats["text"].fillna("", inplace=True)
        mat = tf_vectorizer.fit_transform(feats["text"])

        feats.drop(columns=["name", "description", "text"], inplace=True)
        vectors = concat_feat(feats, mat)
        self.vectors = vectors

        self.save_all_dataframe()
        self.save_vectors(vectors)
        print("Done")

    def get_user_activities(self, user_id, action="like"):
        return self.activity_df[(self.activity_df["user_id"] == user_id) & (self.activity_df["type"] == action)]

    def get_last_video(self, user_id, n=100):
        user_filter = self.history_df["user_id"] == user_id
        videos = self.history_df[user_filter]
        return videos

    def recommend_for_vid(self, video_id, length=10):
        idx = np.where(self.video_df["id"] == video_id)[0]
        if idx:
            ifx = idx[0]
        else:
            return "not found"
        most_similar_with = [
            (
                i,
                consine_sim(self.vectors[idx], self.vectors[i])
            ) for i in range(len(self.vectors))
        ]

        bests = sorted(most_similar_with, reverse=True, key=lambda x: x[1])[0: length + 1]

        return [
            {
                "video_id": int(self.video_df.iloc[best[0]]["id"]),
                "name": str(self.video_df.iloc[best[0]]["name"]),
                "score": float(best[1]) if best[1] != 1 else "input",
            } for best in bests
        ]

engine = Recommender()
# engine.connect(app.mysql)
engine.load_vectors()
engine.init_all_dataframe()

#  ================ export ================ #
def recommend_for_video(video_id):
    return engine.recommend_for_vid(video_id)


def recommend_for_user(user_id):
    return 1