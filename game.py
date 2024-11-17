from uuid import UUID
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import random
import re

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
    def __init__(self, id):
        self.id = id
        self.p1 = None
        self.p2 = None


def new_uuid():
    return UUID(bytes=os.urandom(16), version=4)


@app.get("/api/creategame")
async def create_game():
    game_id = str(random.randint(100000, 999999))

    while game_id in games:
        game_id = str(random.randint(100000, 999999))

    games[game_id] = GameData(game_id)

    return game_id


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


async def send_to_player(identifier: str, message: str):
    print(f"Sending to identifier: {identifier}")
    try:
        target_uuid = UUID(identifier)
        connection = manager.active_connections.get(target_uuid)
        if connection:
            await manager.send_message(message, connection["websocket"])
            return f"Message sent to user with UUID: {identifier}"
    except ValueError:
        pass

    target_uuid, websocket = manager.find_by_name(identifier)
    if websocket:
        await manager.send_message(message, websocket)
        return f"Message sent to user with name: {identifier}"

    return f"User with identifier '{identifier}' not found."


@app.websocket("/ws/{user_uuid}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_uuid: str, user_name: str):
    try:
        user_uuid = UUID(user_uuid)
    except ValueError:
        await websocket.close(code=1003)
        raise HTTPException(status_code=400, detail="Invalid UUID")

    if (
        not user_name
        or len(user_name) > 20
        or not re.match(r"^[a-zA-Z0-9_.-]*$", user_name)
    ):
        user_name = "Anonymous"

    await manager.connect(websocket, user_uuid, user_name)
    print(f"User {user_uuid} (named {user_name}) connected.")

    try:
        while True:
            data = await websocket.receive_text()
            # THIS IS HOW WE GET DATA BACK FROM THE USER & PARSE IT: VV
            print(f"User {user_uuid} (named {user_name}) sent: {data}")
            await manager.send_message(f"Message from {user_name}: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(user_uuid)
        print(f"User {user_uuid} (named {user_name}) disconnected.")
