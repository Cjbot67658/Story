import os
from pymongo import MongoClient, ReturnDocument

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "storybot")
mc = MongoClient(MONGO_URI)
db = mc[DB_NAME]

def increment_category_counter(category_id, code):
    res = db.categories.find_one_and_update(
        {"_id": category_id},
        {"$inc": {"count": 1}, "$setOnInsert": {"code": code, "name": category_id}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return res
