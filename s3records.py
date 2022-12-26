from io import BytesIO
import boto3
from urllib.parse import urlparse
import json


class S3Records(object):
    def __init__(self, path: str):
        self.s3_client = boto3.client('s3')
        
        urlparts = urlparse(path)
        self.bucket = urlparts.netloc
        self.key = urlparts.path.lstrip('/')
        self.data = self.load(path)



    def load(self, path:str):
        fileobj = BytesIO()

        self.s3_client.download_fileobj(self.bucket, self.key, fileobj)

        data = []
        for line in fileobj.getvalue().decode('utf-8').strip().split('\n'):
            try: 
                data.append(json.loads(line))
            except json.decoder.JSONDecodeError:
                pass
        return data



    def save(self):
        fileobj = BytesIO()
        fileobj.write(
            '\n'.join([json.dumps(d) for d in self.data]).encode('utf-8')
        )
        fileobj.seek(0)
        self.s3_client.upload_fileobj(
            fileobj, self.bucket, self.key
        )
