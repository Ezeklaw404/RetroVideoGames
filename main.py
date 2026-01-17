from fastapi import FastAPI, HTTPException, status
from game import Game
from user import User, UserUpdate, UserCreate
app = FastAPI()


# internal data
games = {}
users = {}
game_count = 1
user_count = 1





@app.post("/games", response_model=Game, status_code=status.HTTP_201_CREATED)
def create_game(game: Game):
    global game_count

    game.id = game_count
    games[game_count] = game
    game_count += 1

    return game


@app.put("/games/{gameId}", response_model=Game)
def replace_game(gameId: int, game: Game):
    if gameId not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game.id = gameId
    games[gameId] = game
    return game


@app.patch("/games/{gameId}", response_model=Game)
def update_game(gameId: int, game: Game):
    if gameId not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    stored_game = games[gameId]

    updated_data = game.dict(exclude_unset=True)
    updated_game = stored_game.copy(update=updated_data)

    games[gameId] = updated_game
    return updated_game


@app.delete("/games/{gameId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(gameId: int):
    if gameId not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    del games[gameId]





@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    global user_count

    new_user = User(
        id=user_count,
        name=user.name,
        email=user.email,
        address=user.address
    )

    users[user_count] = new_user
    user_count += 1

    return new_user


@app.put("/users/{userId}", response_model=User)
def replace_user(userId: int, user: UserUpdate):
    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    existing = users[userId]

    updated_user = User(
        id=userId,
        name=user.name if user.name is not None else existing.name,
        email=existing.email,
        address=user.address if user.address is not None else existing.address
    )

    users[userId] = updated_user
    return updated_user


@app.patch("/users/{userId}", response_model=User)
def update_user(userId: int, user: UserUpdate):
    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    existing = users[userId]

    updated_user = existing.copy(update=user.dict(exclude_unset=True))
    users[userId] = updated_user

    return updated_user


@app.delete("/users/{userId}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(userId: int):
    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    del users[userId]