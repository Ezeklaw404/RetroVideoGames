from pymongo import MongoClient

client = MongoClient("mongodb+srv://dev:dev@cluster0.arukagi.mongodb.net/")
db = client["RetroGames"]

users_collection = db["Users"]
games_collection = db["Games"]