
  # Video recommender - content-based filtering

  ## 1. Hệ Thống Khuyến Nghị



  ## 1. Build feature vectors

  By Nguyen Quang Vu (vunquitk11@gmail.com)

  The used features for similarity measurement are:

  1. likes

  2. dislikes

  3. views

  4. duration: video duration in minute

  5. category_id: id of video's category, check table categories for more detail.

  6. comments: comments count

  7. name: name of video in text

  8. description: description of video in text
    
  In these features, `name` and `description` are text format, we will use TFIDF vectorizer to encode it into vectors, then concatenate with remain features.

  ## TODO

  - [ ] Filter videos user already viewed

  - [ ] Improve performance

  - [ ] Sort by similarity
  # module-recommendation
  # module-recommendation
