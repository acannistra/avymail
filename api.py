from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from s3records import S3Records
from datetime import datetime
from typing import Optional
from typing import List
from copy import deepcopy


S3_STORE = "s3://avymail/records.txt"

class Recipient(BaseModel):
    email: str
    center_id: str
    zone_id: str
    data_last_updated_time: Optional[datetime]

def remove_timestamps(data: List[Recipient]) -> List[Recipient]:
    for d in data:
        d['data_last_updated_time'] = None
    return data

app = FastAPI()


@app.post('/add', status_code=201)
async def add_recipient(r: Recipient):
    db = S3Records(S3_STORE)
    db.data.append(r.dict())
    db.save()
    return {"message": "success", "recipient": r}

@app.post('/remove', status_code=200)
async def remove_recipient(r: Recipient):
    db = S3Records(S3_STORE)
    try:
        r.data_last_updated_time = None
        data_copied = deepcopy(db.data)
        data_copied = remove_timestamps(data_copied)
        idx = data_copied.index(r.dict())
        del db.data[idx]
        db.save()
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{r.json()} not found")
    
    return {"message": "success"}
    
        

