import boto3
import io
import os

print('Loading function')


def get_text(response):
    blocks = response['Blocks']

    # List to hold detected text
    detected_text = []

    # Display block information and add detected text to list
    for block in blocks:
        if 'Text' in block and block['BlockType'] == "LINE":
            detected_text.append(block['Text'])

    return detected_text


def process_text_detection(s3_connection, client, bucket, document):
    # Get the document from S3  
    # s3_object = s3_connection.Object(bucket, document)
    # s3_response = s3_object.get()
    # 
    # stream = io.BytesIO(s3_response['Body'].read())
    # image = Image.open(stream)

    # Detect text in the document
    # Process using S3 object'
    response = client.detect_document_text(
        Document={'S3Object': {'Bucket': bucket, 'Name': document}})

    text = get_text(response)
    return text


def lambda_handler(event, context):
    session = boto3.Session()
    s3_connection = session.resource('s3')
    client = session.client('textract')
    document = event["S3_FILE_NAME"] or os.environ['S3_FILE_NAME']
    bucket = event["S3_BUCKET_NAME"] or os.environ['S3_BUCKET_NAME']

    text = process_text_detection(s3_connection, client, bucket, document)
    print(text)


if __name__ == "__main__":
    lambda_handler({}, {})
