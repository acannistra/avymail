from io import BytesIO
import boto3
from urllib.parse import urlparse
import json
from prometheus_client import Gauge

num_records_gauge = Gauge(
    "s3records_num_records",
    "number of records in S3Records",
    labelnames=["record_loc", "center"],
)


def get_center_metrics(data, label):
    center_counts = dict()
    for obj in data:
        center_id = obj.get("center_id")
        center_counts[center_id] = center_counts.get(center_id, 0) + 1

    for center in center_counts.keys():
        num_records_gauge.labels(label, center).set(center_counts[center])


class S3Records(object):
    def __init__(self, path: str):
        self.s3_client = boto3.client("s3")

        urlparts = urlparse(path)
        self.bucket = urlparts.netloc
        self.key = urlparts.path.lstrip("/")
        self.data = self.load(path)
        self._prom_gauge_label = f"{self.bucket}/{self.key}"
        get_center_metrics(self.data, self._prom_gauge_label)

    def load(self, path: str):
        fileobj = BytesIO()

        self.s3_client.download_fileobj(self.bucket, self.key, fileobj)

        data = []
        for line in fileobj.getvalue().decode("utf-8").strip().split("\n"):
            try:
                data.append(json.loads(line))
            except json.decoder.JSONDecodeError:
                pass

        return data

    def save(self):
        fileobj = BytesIO()
        fileobj.write("\n".join([json.dumps(d) for d in self.data]).encode("utf-8"))
        fileobj.seek(0)
        self.s3_client.upload_fileobj(fileobj, self.bucket, self.key)
