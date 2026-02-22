from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId

from db.clients.mongo import MongodbServices

router = APIRouter()



data = [
    {
        "id": 1,
        "name": "zxc",
        "email": "zcx@gmail.ocm",
    },
    {
        "id": 2,
        "name": "abbos",
        "email": "abbos@gmail.com",
    },
    {
     "username": "lejoshua",
     "name": "Michael Johnson",
     "address": "15989 Edward Inlet\nLake Maryton, NC 39545",
     "birthdate": {"$date": 54439275000},
     "email": "courtneypaul@example.com",
     "accounts": [
       470650,
       443178
     ],
     "tier_and_details": {
       "b5f19cb532fa436a9be2cf1d7d1cac8a": {
          "tier": "Silver",
          "benefits": [
            "dedicated account representative"
          ],
          "active": True,
          "id": "b5f19cb532fa436a9be2cf1d7d1cac8a"
          }
     }
    },
]




class ItemCreate(BaseModel):
    name: str
    data: dict = {}


def get_collection():
    db = MongodbServices.get_mongo_db()
    return db["items"]


@router.post("/", status_code=201, deprecated=True)
async def create_item(item: ItemCreate):
    collection = get_collection()
    result = await collection.insert_one(item.model_dump())
    return {"id": str(result.inserted_id), "message": "Created"}


@router.get("/")
async def get_items():
    collection = get_collection()
    items = []
    async for doc in collection.find():
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.get("/{item_id}")
async def get_item(item_id: str):
    collection = get_collection()
    try:
        doc = await collection.find_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    doc["_id"] = str(doc["_id"])
    return doc


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    collection = get_collection()
    try:
        result = await collection.delete_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"message": "Deleted"}