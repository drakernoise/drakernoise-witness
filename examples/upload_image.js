import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import fs from "fs";
import path from "path";

const s3 = new S3Client({
    region: "us-east-1", // MinIO requires a region, though ignored
    endpoint: "https://media.drakernoise.com",
    credentials: {
        accessKeyId: "YOUR_ACCESS_KEY",
        secretAccessKey: "YOUR_SECRET_KEY"
    }
});

async function uploadImage(filePath) {
    const fileName = path.basename(filePath);
    const fileContent = fs.readFileSync(filePath);

    const command = new PutObjectCommand({
        Bucket: "public-assets",
        Key: fileName,
        Body: fileContent
    });

    try {
        await s3.send(command);
        console.log(`Successfully uploaded s3://public-assets/${fileName}`);
        console.log("Public delivery URL depends on your bucket policy and gateway mapping.");
        return `s3://public-assets/${fileName}`;
    } catch (err) {
        console.error("Error uploading file:", err);
    }
}

// Usage
uploadImage("./test_image.jpg");
