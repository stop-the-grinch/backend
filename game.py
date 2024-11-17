from uuid import UUID
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import random
import re
import json
from typing import Union

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

games = {}


class GameData:
    def __init__(self, id, creator):
        self.id = str(id)
        self.state = "LOBBY"
        self.creator = str(creator)
        self.p1 = str(creator)
        self.p1FriendlyName = uuid_to_name(creator)
        self.p2 = None
        self.p2FriendlyName = None


def new_uuid():
    return UUID(bytes=os.urandom(16), version=4)


@app.post("/api/create-game/{player_uuid}")
async def create_game(player_uuid: UUID):
    existing_lobby = await does_player_lobby_exist(player_uuid)

    if existing_lobby:
        raise HTTPException(
            status_code=403, detail=f"You have an existing lobby: {existing_lobby}"
        )
    game_id = str(random.randint(100000, 999999))

    while game_id in games:
        game_id = str(random.randint(100000, 999999))

    # create the game
    games[game_id] = GameData(game_id, player_uuid)

    print("New game: " + game_id)
    await send_to_player(
        str(player_uuid), games[game_id].__dict__
    )  # Convert UUID to string

    return {"game_id": game_id}


@app.post("/api/start-game/{game_code}")
async def start_game(game_code: str):
    if not await does_lobby_exist(game_code):
        raise HTTPException(
            status_code=403, detail=f"Can't start -- that lobby doesn't exist!"
        )
    game = games[game_code]
    game.state = "GAME"
    await send_to_player(game.p1, game.__dict__)
    await send_to_player(game.p2, game.__dict__)
    return


@app.post("/api/join-game/{player_uuid}/{game_code}")
async def join_game(player_uuid: UUID, game_code: str):
    if not await does_lobby_exist(game_code):
        raise HTTPException(status_code=403, detail=f"That lobby doesn't exist!")
    # user shouldn't be in any other lobby
    if await is_player_in_game(player_uuid) != False:
        raise HTTPException(status_code=403, detail=f"Don't join two games at once!")
    if games[game_code].p1 is not None and games[game_code].p2 is not None:
        raise HTTPException(status_code=403, detail=f"That lobby is full!")

    games[game_code].p2 = str(player_uuid)
    games[game_code].p2FriendlyName = uuid_to_name(player_uuid)

    print("Sending to player " + str(player_uuid))
    await send_to_player(str(player_uuid), games[game_code].__dict__)
    await send_to_player(games[game_code].p1, games[game_code].__dict__)
    return {"game_code": game_code}


@app.post("/api/leave-game/{player_uuid}/")
async def leave_button(player_uuid: UUID):
    game_id = await is_player_in_game(player_uuid)
    if not game_id:
        raise HTTPException(status_code=403, detail="You're not in a game! Refresh?")

    game = games[game_id]

    if str(player_uuid) == game.p1:
        await send_to_player(UUID(game.p1), None)

        if game.p2:
            game.p1 = game.p2
            game.p1FriendlyName = game.p2FriendlyName
            game.p2 = None
            game.p2FriendlyName = None
        else:
            del games[game_id]
            return

    elif str(player_uuid) == game.p2:
        await send_to_player(UUID(game.p2), None)

        game.p2 = None
        game.p2FriendlyName = None
    else:
        raise HTTPException(status_code=403, detail="You're not part of this game!")

    if game.p1:
        await send_to_player(game.p1, game.__dict__)
    if game.p2:
        await send_to_player(game.p2, game.__dict__)

    return


@app.get("/api/join/{game_code}")
async def join(game_code):
    return "joining game code " + str(game_code)


@app.get("/api/games/")
async def retAllGames():
    game_ids = []
    for game in games.values():
        game_ids.append(game.id)
    return game_ids


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, dict] = {}

    async def connect(self, websocket: WebSocket, user_uuid: UUID, user_name: str):
        await websocket.accept()
        self.active_connections[user_uuid] = {
            "websocket": websocket,
            "user_name": user_name,
        }
        print(f"Connected users: {self.active_connections}")

    def disconnect(self, user_uuid: UUID):
        if user_uuid in self.active_connections:
            del self.active_connections[user_uuid]

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection["websocket"].send_text(message)

    def find_by_name(self, user_name: str):
        for uuid, data in self.active_connections.items():
            print(f"Checking user_name: {data['user_name']}")
            if data["user_name"] == user_name:
                return uuid, data["websocket"]
        return None, None


manager = ConnectionManager()


@app.post("/api/demo-send/")
async def demo_send(identifier: str, message: str):
    result = await send_to_player(identifier, message)
    return {"status": result}


async def does_player_lobby_exist(uuid):
    for game in games.values():
        if game.creator == str(uuid):
            return game.id
    return False


def uuid_to_name(user_uuid: Union[str, UUID]):
    if isinstance(user_uuid, str):
        try:
            user_uuid = UUID(user_uuid)
        except ValueError:
            return None
    connection = manager.active_connections.get(user_uuid)
    if connection:
        return connection["user_name"]
    else:
        return None


async def does_lobby_exist(code):
    for game in games.values():
        if game.id == code:
            return True
    return False


async def is_player_in_game(player_uuid: UUID):
    for game in games.values():
        if (game.p1 and UUID(game.p1) == player_uuid) or (
            game.p2 and UUID(game.p2) == player_uuid
        ):
            return game.id
    return False


async def send_to_player(identifier: Union[str, UUID], message: dict):
    print(f"Sending to identifier: {identifier}")
    try:
        if isinstance(identifier, UUID):
            target_uuid = identifier
        else:
            target_uuid = UUID(identifier)
        connection = manager.active_connections.get(target_uuid)
        if connection:
            # Convert UUIDs in the message to strings
            serialized_message = json.dumps(
                message, default=lambda o: str(o) if isinstance(o, UUID) else o
            )
            await manager.send_message(serialized_message, connection["websocket"])
            return f"Message sent to user with UUID: {identifier}"
    except ValueError:
        pass

    target_uuid, websocket = manager.find_by_name(str(identifier))
    if websocket:
        serialized_message = json.dumps(
            message, default=lambda o: str(o) if isinstance(o, UUID) else o
        )
        await manager.send_message(serialized_message, websocket)
        return f"Message sent to user with name: {identifier}"

    return f"User with identifier '{identifier}' not found."


@app.websocket("/ws/{user_uuid}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: UUID, user_name: str):
    if (
        not user_name
        or len(user_name) > 20
        or not re.match(r"^[a-zA-Z0-9_.-]*$", user_name)
    ):
        user_name = "Anonymous"

    await manager.connect(websocket, user_uuid, user_name)
    print(f"User {user_uuid} (named {user_name}) connected.")

    game_id = await is_player_in_game(user_uuid)

    print("USER!! " + str(game_id))

    if game_id:
        await send_to_player(user_uuid, games[game_id].__dict__)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"User {user_uuid} (named {user_name}) sent: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_uuid)
        print(f"User {user_uuid} (named {user_name}) disconnected.")
