from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI() # This sets up the FastAPI application instance


users: list[dict] = [
    {"username": "admin", "password": "esihfuoasie"},
    {"username": "user0", "password": "aiohefoiaef"},
    {"username": "user1", "password": "efohiaeoihf"},
    {"username": "user2", "password": "aeihfahef"},
    {"username": "user3", "password": "ruioghsaghr"},
    {"username": "user4", "password": "efgWEIGGaewrfa"},
]

users_names = {user['username']: user for user in users}

@app.get("/")
def read_root():
    '''
    Root endpoint

    :return: A simple JSON response with a greeting message
    '''
    return { "message": "Hello World" }

@app.get("/user/{username}", response_class=HTMLResponse)
def read_user(username: str):

    username = username.lower()

    if not username in users_names:
        raise HTTPException(status_code=404, detail="User not found")

    return f"<h1>Hello {username}</h1> <p>Here is your password {users_names[username]['password']}</p>"
