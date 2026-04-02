#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://localhost:18012"


def get_token(ak: str, sk: str) -> str:
    response = requests.post(
        f"{BASE_URL}/get_token",
        json={"ak": ak, "sk": sk}
    )
    response.raise_for_status()
    return response.json()["token"]


def get_collection_info(token: str, database: str, collection_name: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/get_collection_info",
        json={"database": database, "collection_name": collection_name},
        headers={"X-Token": token}
    )
    response.raise_for_status()
    return response.json()


def search_data(token: str, database: str, collection_name: str, search_word: str, top_k: int = 10) -> dict:
    response = requests.post(
        f"{BASE_URL}/search",
        json={
            "database": database,
            "collection_name": collection_name,
            "search_word": search_word,
            "top_k": top_k
        },
        headers={"X-Token": token}
    )
    response.raise_for_status()
    return response.json()


def main():
    ak = "dev"
    sk = "dEv#1234"
    database = "default"
    collection_name = "XiXiang_DiMian_2"
    search_word = "气象质量管理"

    print("=" * 50)
    print("Step 1: Get Token")
    print("=" * 50)
    token = get_token(ak, sk)
    print(f"Token: {token}")

    print("\n" + "=" * 50)
    print("Step 2: Get Collection Info")
    print("=" * 50)
    collection_info = get_collection_info(token, database, collection_name)
    print(json.dumps(collection_info, indent=2, ensure_ascii=False))

    print("\n" + "=" * 50)
    print("Step 3: Search Data")
    print("=" * 50)
    results = search_data(token, database, collection_name, search_word)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
