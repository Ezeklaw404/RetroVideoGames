from fastapi import FastAPI, HTTPException, status, Response
from pymongo import ReturnDocument
import bcrypt
from confluent_kafka import Producer
import json
from bson import ObjectId
from app.request import Request, RequestCreate, AcceptRequest
from app.game import Game, GameCreate, GameUpdate
from app.user import User, UserUpdate, UserCreate
from app.db import users_collection, games_collection, requests_collection
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

BASE_URL = "http://127.0.0.1:8080"


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ---------- GAMES ----------

@app.get("/games", response_model=list[Game])
def get_games():
    print("------------------ get games")
    games = []

    for g in games_collection.find():
        game_id = str(g["_id"])
        g.pop("_id")


        games.append({
            "id": game_id,
            **g,
            "owner": f"{BASE_URL}/users/{g['owner_id']}"
        })

    return games


@app.get("/games/{game_id}", response_model=Game)
def get_game_by_id(game_id: str):
    print("------------------ get game by id")
    game = games_collection.find_one({"_id": ObjectId(game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game_id_str = str(game["_id"])
    game.pop("_id")

    return {
        "id": game_id_str,
        **game,
        "owner": f"{BASE_URL}/users/{game['owner_id']}",
    }

@app.get("/games/owner/{owner_id}", response_model=list[Game])
def get_games_by_owner(owner_id: str):
    print("------------------ get games by owner")
    games_cursor = games_collection.find({"owner_id": owner_id})
    games_list = []

    for g in games_cursor:
        game_id_str = str(g["_id"])
        g.pop("_id")
        games_list.append({
            "id": game_id_str,
            **g,
            "owner": f"{BASE_URL}/users/{g['owner_id']}"
        })

    if not games_list:
        raise HTTPException(status_code=404, detail="No games found for this owner")

    return games_list

@app.get("/games/name/{game_name}", response_model=Game)
def get_game_by_name(game_name: str):
    print("------------------ get game by name")
    game = games_collection.find_one({"name": {"$regex": game_name, "$options": "i"}})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game_id_str = str(game["_id"])
    game.pop("_id")

    return {
        "id": game_id_str,
        **game,
        "owner": f"{BASE_URL}/users/{game['owner_id']}",
    }


@app.post("/games", response_model=Game, status_code=status.HTTP_201_CREATED)
def create_game(game: GameCreate):
    print("------------------ new game")
    new_game = game.dict()
    result = games_collection.insert_one(new_game)

    game_id = str(result.inserted_id)

    return {
        "id": game_id,
        **new_game,
        "owner": f"{BASE_URL}/users/{game.owner_id}"
    }


@app.patch("/games/{game_id}", response_model=Game)
def update_game(game_id: str, game: GameUpdate):
    print("------------------ patch game")
    update_data = game.dict(exclude_unset=True)

    updated_game = games_collection.find_one_and_update(
        {"_id": ObjectId(game_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )

    if not updated_game:
        raise HTTPException(status_code=404, detail="Game not found")


    return {
        "id": game_id,
        **updated_game,
        "owner": f"{BASE_URL}/users/{updated_game['owner_id']}",
    }
    


@app.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: str):
    print("------------------ delete game")
    result = games_collection.delete_one({"_id": ObjectId(game_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Game not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- USERS ----------

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str):
    print("------------------ get user, by id")
    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.pop("_id")

    return {
        "id": user_id,
        **user,
        "links": {
            "games": f"{BASE_URL}/games/owner/{user_id}",
            "requests": f"{BASE_URL}/requests/client/{user_id}"
        }
        
    }


@app.post("/user", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    print("------------------ new user")
    new_user = user.dict()
    result = users_collection.insert_one(new_user)

    user_id = str(result.inserted_id)

    return {
        "id": user_id,
        **new_user,
    }


@app.patch("/users/{user_id}", response_model=User)
def update_user(user_id: str, user: UserUpdate):
    print("------------------ patch user")
    update_data = user.dict(exclude_unset=True)

    password_changed = False


    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
        password_changed = True

    updated_user = users_collection.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=True
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Send to kafka only if password actually changed
    if password_changed:
        event = {
            "event_type": "PASSWORD_CHANGED",
            "recipients": [updated_user["email"]],
            "subject": "Your password was changed",
            "body": "Your Retro Game Exchange password was successfully updated."
        }

        send_notification(event)

    updated_user.pop("_id")

    return {
        "id": user_id,
        **updated_user,
    }


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str):
    print("------------------ delete user")
    result = users_collection.delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- REQUESTS ----------

@app.get("/requests/{request_id}", response_model=Request)
def get_request(request_id: str):
    print("------------------ get request")
    request_doc = requests_collection.find_one({"_id": ObjectId(request_id)})

    if not request_doc:
        raise HTTPException(status_code=404, detail="No Requests found")

    return {
        "id": request_id,
        "requester": f"{BASE_URL}/users/{request_doc['requesterId']}",
        "requestedGame": f"{BASE_URL}/games/{request_doc['requestedGameId']}",
        "offeredGame": f"{BASE_URL}/games/{request_doc['offeredGameId']}",
        "client": f"{BASE_URL}/users/{request_doc['clientId']}",
        "accepted": request_doc['accepted']
    }


@app.get("/requests/client/{client_id}", response_model=Request)
def get_request(client_id: str):
    print("------------------ get request")
    request_doc = requests_collection.find_one({"clientId": client_id})

    if not request_doc:
        raise HTTPException(status_code=404, detail="No Requests found")

    return {
        "id": str(request_doc['_id']),
        "requester": f"{BASE_URL}/users/{request_doc['requesterId']}",
        "requestedGame": f"{BASE_URL}/games/{request_doc['requestedGameId']}",
        "offeredGame": f"{BASE_URL}/games/{request_doc['offeredGameId']}",
        "client": f"{BASE_URL}/users/{client_id}",
        "accepted": request_doc['accepted']
    }


@app.post("/requests", response_model=Request, status_code=status.HTTP_201_CREATED)
def create_request(req: RequestCreate):
    print("------------------ new request")

    new_request = req.dict()
    new_request['accepted'] = False

    result = requests_collection.insert_one(new_request)
    request_id = str(result.inserted_id)


    requester = users_collection.find_one({"_id": ObjectId(req.requesterId)})
    client = users_collection.find_one({"_id": ObjectId(req.clientId)})

    if requester and client:
        event = {
            "event_type": "OFFER_CREATED",
            "recipients": [requester["email"], client["email"]],
            "subject": "New Video Game Offer Created",
            "body": "A new offer has been created in Retro Game Exchange."
        }

        send_notification(event)

    return {
        "id": request_id,
        "requester": f"{BASE_URL}/users/{req.requesterId}",
        "requestedGame": f"{BASE_URL}/games/{req.requestedGameId}",
        "offeredGame": f"{BASE_URL}/games/{req.offeredGameId}",
        "client": f"{BASE_URL}/users/{req.clientId}",
        "accepted": False
    }




@app.patch("/requests/{request_id}", response_model=Request)
def accept_request(request_id: str, body: AcceptRequest):
    print("------------------ request accepted")

    # First, find and update the request to accepted
    updated_request = requests_collection.find_one_and_update(
        {"_id": ObjectId(request_id)},
        {"$set": {"accepted": body.accepted}},
        return_document=True
    )

    if not updated_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Only swap games if True
    if body.accepted:
        requested_game = games_collection.find_one({"_id": ObjectId(updated_request["requestedGameId"])})
        offered_game   = games_collection.find_one({"_id": ObjectId(updated_request["offeredGameId"])})

        if not requested_game or not offered_game:
            raise HTTPException(status_code=404, detail="One of the games not found")

        requested_owner_id = requested_game["owner_id"]
        offered_owner_id   = offered_game["owner_id"]

        games_collection.update_one(
            {"_id": requested_game["_id"]},
            {
                "$set": {"owner_id": offered_owner_id},
                "$inc": {"previousOwnerCount": 1}
            }
        )

        games_collection.update_one(
            {"_id": offered_game["_id"]},
            {
                "$set": {"owner_id": requested_owner_id},
                "$inc": {"previousOwnerCount": 1}
            }
        )

    requester = users_collection.find_one({"_id": ObjectId(updated_request["requesterId"])})
    client = users_collection.find_one({"_id": ObjectId(updated_request["clientId"])})

    if requester and client:
        if body.accepted:
            event_type = "OFFER_ACCEPTED"
            subject = "Offer Accepted"
            message = "Your video game offer has been accepted."
        else:
            event_type = "OFFER_REJECTED"
            subject = "Offer Rejected"
            message = "Your video game offer has been rejected."

        event = {
            "event_type": event_type,
            "recipients": [requester["email"], client["email"]],
            "subject": subject,
            "body": message
        }

        send_notification(event)

    return {
        "id": request_id,
        "requester": f"{BASE_URL}/users/{updated_request['requesterId']}",
        "requestedGame": f"{BASE_URL}/games/{updated_request['requestedGameId']}",
        "offeredGame": f"{BASE_URL}/games/{updated_request['offeredGameId']}",
        "client": f"{BASE_URL}/users/{updated_request['clientId']}",
        "accepted": body.accepted
    }


@app.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(request_id: str):
    print("------------------ get request")
    result = requests_collection.delete_one({"_id": ObjectId(request_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)










config = {
    'bootstrap.servers': 'kafka:9092',
    'acks': 'all'
}

producer = Producer(config)

def delivery_callback(err, msg):
    if err:
        print(f'Delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()}')

def send_notification(event):
    producer.produce(
        topic='notifications',
        key=event['event_type'],
        value=json.dumps(event),
        callback=delivery_callback
    )
    producer.poll(0)

    producer.flush()



