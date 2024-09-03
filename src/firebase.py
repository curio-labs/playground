import os

import httpx


def get_firebase_token():
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    querystring = {"key": os.environ["FIREBASE_API_KEY"]}
    payload = {
        "email": os.environ["CURIO_AI_ADMIN_EMAIL"],
        "password": os.environ["CURIO_AI_ADMIN_PASSWORD"],
        "returnSecureToken": True,
    }
    headers = {"Content-Type": "application/json", "User-Agent": "insomnia/8.6.1"}

    response = httpx.post(url, json=payload, headers=headers, params=querystring)

    return response.json()["idToken"]
