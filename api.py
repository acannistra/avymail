from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from pydantic import EmailStr
from s3records import S3Records
from datetime import datetime
from typing import Optional
from typing import List
from copy import deepcopy
from cachetools import func


import avalanche

S3_STORE = "s3://avymail/records.txt"

@func.ttl_cache(maxsize=1, ttl=3600)
def get_avalanche_api() -> avalanche.AvalancheAPI:
    return avalanche.AvalancheAPI()


class Recipient(BaseModel):
    email: EmailStr
    center_id: str
    zone_id: str
    data_last_updated_time: Optional[datetime]

def remove_timestamps(data: List[Recipient]) -> List[Recipient]:
    for d in data:
        d['data_last_updated_time'] = None
    return data

app = FastAPI()

CORS_ORIGINS = [
    "https://anthonycannistra.com",
    "http://anthonycannistra.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def find_record(r: Recipient, db: List[Recipient]):
    this_r = deepcopy(r)
    this_r.data_last_updated_time = None
    data_copied = deepcopy(db.data)
    data_copied = remove_timestamps(data_copied)
    idx = data_copied.index(this_r.dict())
    return idx

@app.post('/add', status_code=201)
async def add_recipient(r: Recipient):
    db = S3Records(S3_STORE)
    try:
        find_record(r, db)
    except ValueError:
        # if ValueError then we don't have sub
        db.data.append(r.dict())
        db.save()
        return {"message": "success", "recipient": r}
    
    raise HTTPException(status_code=409, detail="Record already exists.")
    

@app.get('/remove', status_code=200)
async def remove_recipient(r: Recipient = Depends()):
    db = S3Records(S3_STORE)
    try:
        idx = find_record(r, db)
        del db.data[idx]
        db.save()
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{r.json()} not found")
    
    return {"message": "success"}
    
@app.get('/subs')
async def remove_recipient(email: str):
    db = S3Records(S3_STORE)
    relevant_records = [r for r in db.data if r['email'] == email]
    return relevant_records


SUPPORTED_ZONES = [
    "Northwest Avalanche Center",
    "Central Oregon Avalanche Center",
    "Sawtooth Avalanche Center",
    "Bridger-Teton Avalanche Center"
]
        
@app.get('/zones')
async def zones():
    a = get_avalanche_api()
    return {k:v for k,v in a.centers.items() if k in SUPPORTED_ZONES}
