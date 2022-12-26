from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from s3records import S3Records


S3_STORE = "s3://avymail/records.txt"

class Recipient(BaseModel):
    email: str
    center: str
    zone_id: str

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
        idx = db.data.index(r.dict())
        del db.data[idx]
        db.save()
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{r.json()} not found")
    
        

