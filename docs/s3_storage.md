# Decentralized Storage (S3-Compatible)

We provide an S3-compatible object storage service powered by **MinIO**.
This service is intended for approved developers who need object storage behind Drakernoise infrastructure.

## Connection Details

| Parameter | Value |
| :--- | :--- |
| **API Endpoint** | `https://media.drakernoise.com` |
| **Region** | `us-east-1` (Default) |
| **SSL** | Yes (Required) |


> [!NOTE]
> `images.drakernoise.com` is a public asset gateway, not the canonical S3 API endpoint.

## Access Policy
Access is currently **Invite Only** for active Blurt developers.
Contact **@drakernoise** on Discord/Blurt to request your `Access Key` and `Secret Key`.

## Integration

### Python (boto3)
```python
import boto3
from botocore.client import Config

s3 = boto3.client('s3',
    endpoint_url='https://media.drakernoise.com',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    config=Config(signature_version='s3v4')
)

# Upload image
s3.upload_file('local_image.jpg', 'public-assets', 'remote_image.jpg')
print("Upload completed. Public delivery URL depends on your bucket and gateway mapping.")
```

### JavaScript (AWS SDK v3)
```javascript
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const s3 = new S3Client({
    region: "us-east-1",
    endpoint: "https://media.drakernoise.com",
    credentials: {
        accessKeyId: "YOUR_ACCESS_KEY",
        secretAccessKey: "YOUR_SECRET_KEY"
    }
});
```
