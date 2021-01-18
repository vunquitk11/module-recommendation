import os
import pandas as pd
import numpy as np
import scipy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter

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


def sort_by_score(videos):
    videos = [dict(vid) for vid in set(tuple(item.items()) for item in videos)]
    videos = sorted(videos, key=lambda x: x["score"], reverse=True)

    return videos


def filter_viewed_videos(videos, viewed_ids):
    res = []
    for vid in videos:
        if vid["video_id"] not in viewed_ids:
            res.append(vid)

    return res


def to_str(list_of_int):
    return [str(c) for c in list_of_int]


def compute_dist(values):
    counts = dict(Counter(values))
    total = len(values)
    dist_map = {k: v / total for k, v in counts.items()}
    return dist_map


def weighted_by_category(videos, category_map):
    weight_map = compute_dist(list(category_map.values()))
    for vid in videos:
        cate = vid["category_id"]
        vid["score"] *= weight_map.get(cate, 0.001)

    return videos

class Recommender:
    def __init__(self):
        self.save_dir = "./storage"
        self.override = False

    def _p(self, fname):
        return os.path.join(self.save_dir, fname)

    def allow_update(self):
        self.override = True

    def connect(self, mysql):
        self.connection = mysql.connect()
        self.cursor = self.connection.cursor()

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
            "id,video_src,thumbnail,name,description,duration,tags,category_id"
        )

    def save_all_dataframe(self):
        for attr in ["history_df", "activity_df", "video_df"]:
            getattr(self, attr).to_csv(self._p(attr + ".csv"))

    def find(self, sql):
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        return data

    def update(self, sql):
        self.cursor.execute(sql)
        self.connection.commit()

    def findone(self, sql):
        self.cursor.execute(sql)
        data = self.cursor.fetchone()
        return data

    def build_df(self, table, columns, condition=""):
        fpath = self._p(table + ".csv")
        if not self.override and os.path.isfile(fpath):
            return pd.read_csv(fpath)

        sql = f"SELECT {columns} from {table}"
        if condition:
            sql += f"WHERE ${condition}"

        data = self.find(sql)

        df = pd.DataFrame(data)
        df.columns = columns.split(",")
        return df

    def build_vectors(self):
        if not self.override:
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

    def recommend_for_user(self, user_id, limit=20):
        sql = f"SELECT user_id,video_id,created_at from watch_histories" \
              f" WHERE user_id = {user_id} ORDER BY created_at DESC LIMIT 20 "

        found_vids = self.find(sql)

        if not found_vids:
            return []

        viewed_ids = [vid[0] for vid in found_vids]
        sql = f"SELECT id,category_id from videos WHERE id IN ({','.join(to_str(viewed_ids))})"
        video_infos = self.find(sql)
        category_map = {v[0]: v[1] for v in video_infos}

        videos = []

        for vid_id in viewed_ids:
            videos += filter_viewed_videos(self.recommend_for_vid(vid_id, 10), viewed_ids)

        if len(videos) and len(videos) < limit:
            rest = limit - len(videos)
            videos += self.recommend_for_vid(videos[0]["video_id"], rest, update_db=False)

        # This function use for calculate category feature
        weighted_by_category(videos, category_map) 
        videos = sort_by_score(videos)

        try:
            rec_ids = f"[{','.join([str(vid['video_id']) for vid in videos])}]"
            # Insert to db
            update_sql = f"UPDATE users SET array_recommend_video = '{rec_ids}' where id = {user_id}"
            self.update(update_sql)
        except Exception as e:
            print("Could not update users table", str(e))

        return videos[:limit]

    def recommend_for_vid(self, video_id, length=10, update_db=True):
        idx = np.where(self.video_df["id"] == video_id)[0]
        if idx:
            ifx = idx[0]
        else:
            return []

        most_similar_with = [
            (
                i,
                consine_sim(self.vectors[idx], self.vectors[i])
            ) for i in range(len(self.vectors))
        ]

        bests = sorted(most_similar_with, reverse=True, key=lambda x: x[1])[1: length + 1]

        results = []
        for best in bests:
            id_, score = best
            vid_df = self.video_df.iloc[id_]
            results.append({
                "video_id": int(vid_df["id"]),
                "name": str(vid_df["name"]),
                "video_src": str(vid_df["video_src"]),
                "thumbnail": str(vid_df["thumbnail"]),
                "category_id": str(vid_df["category_id"]),
                "score": float(score),
            })

        if update_db:
            try:
                rec_ids = f"[{','.join([str(vid['video_id']) for vid in results])}]"
                # Insert to db
                update_sql = f"UPDATE videos SET array_recommend_video = '{rec_ids}' WHERE id = {video_id}"
                self.update(update_sql)
            except Exception as e:
                print("Could not update videos table", str(e))

        return results

engine = Recommender()
# engine.connect(app.mysql)
engine.load_vectors()
engine.init_all_dataframe()

#  ================ export ================ #
def recommend_for_video(video_id, limit=10):
    return engine.recommend_for_vid(video_id, limit)


def recommend_for_user(user_id, limit=10):
    return engine.recommend_for_user(user_id, limit)
