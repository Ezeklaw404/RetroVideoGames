from fastapi import FastAPI, HTTPException, status, Response
import bcrypt
from bson import ObjectId
from game import Game
from user import User, UserUpdate, UserCreate
from db import users_collection, games_collection
app = FastAPI()


BASE_URL = "http://127.0.0.1:8000"

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)




@app.get("/games", response_model=list[Game])
def get_games(name: str | None = None, system: str | None = None, owner_id: str | None = None):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if system:
        query["system"] = system
    if owner_id:
        query["owner_id"] = owner_id 

    results = []
    for g in games_collection.find(query):
        g_id = str(g["_id"])
        g["id"] = g_id
        
        g["links"] = [
            {"rel": "self", "href": f"{BASE_URL}/games/{g_id}"},
            {"rel": "owner", "href": f"{BASE_URL}/users/{g['owner_id']}"}
        ]
        results.append(g)
    return results

@app.get("/games/{game_id}", response_model=Game)
def get_game(game_id: str):
    game = games_collection.find_one({"_id": ObjectId(game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game["id"] = str(game["_id"])
    
    game["links"] = [
        {"rel": "self", "href": f"{BASE_URL}/games/{game['id']}"},
        {"rel": "owner_profile", "href": f"{BASE_URL}/users/{game['owner_id']}"},
        {"rel": "update", "href": f"{BASE_URL}/games/{game['id']}", "method": "PATCH"},
        {"rel": "delete", "href": f"{BASE_URL}/games/{game['id']}", "method": "DELETE"}
    ]
    
    return game

@app.post("/games", response_model=Game, status_code=status.HTTP_201_CREATED)
def create_game(game: Game):
    new_game_data = game.dict(exclude={"id"})
    result = games_collection.insert_one(new_game_data)
    
    game_id = str(result.inserted_id)
    new_game_data["id"] = game_id

    new_game_data["links"] = [
        {"rel": "self", "href": f"/games/{game_id}"},
        {"rel": "owner", "href": f"/users/{game.owner_id}"},
        {"rel": "update", "href": f"/games/{game_id}", "method": "PATCH"},
        {"rel": "delete", "href": f"/games/{game_id}", "method": "DELETE"}
    ]
    return new_game_data

@app.patch("/games/{game_id}", response_model=Game)
def update_game(game_id: str, game: Game):
    update_data = game.dict(exclude_unset=True, exclude={"id"})
    
    updated_game = games_collection.find_one_and_update(
        {"_id": ObjectId(game_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not updated_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    updated_game["id"] = str(updated_game["_id"])
    return updated_game

@app.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: str):
    result = games_collection.delete_one({"_id": ObjectId(game_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Game not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)







# --- USERS ---

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id_str = str(user["_id"])
    
    return {
        "id": user_id_str,
        "name": user["name"],
        "email": user["email"],
        "address": user.get("address"),
        "links": [
            {"rel": "self", "href": f"{BASE_URL}/users/{user_id_str}"},
            {"rel": "owner_games", "href": f"{BASE_URL}/games?owner_id={user_id_str}"}
        ]
    }

@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_create: UserCreate):
    hashed_pw = hash_password(user_create.password)
    
    new_user = {
        "name": user_create.name,
        "email": user_create.email,
        "address": user_create.address,
        "hashed_password": hashed_pw
    }

    result = users_collection.insert_one(new_user)
    new_user["id"] = str(result.inserted_id)
    return new_user

@app.patch("/users/{user_id}", response_model=User)
def update_user(user_id: str, user_update: UserUpdate):
    update_data = user_update.dict(exclude_unset=True)
    
    updated_user = users_collection.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=True
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user["id"] = str(updated_user["_id"])
    return updated_user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)