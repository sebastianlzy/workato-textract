import boto3
import io
import os
import time

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


def get_result(textract_client, jobId):
    max_results = 1000
    pagination_token = None
    finished = False
    detected_texts = []

    while not finished:
        response = None
        if pagination_token is None:
            response = textract_client.get_document_text_detection(JobId=jobId,
                                                                   MaxResults=max_results)
        else:
            response = textract_client.get_document_text_detection(JobId=jobId,
                                                                   MaxResults=max_results,
                                                                   NextToken=pagination_token)

        if response['JobStatus'] != "SUCCEEDED":
            return {
                "statusCode": 200,
                "body": response
            }

        blocks = response['Blocks']
        # Display block information and add detected text to list
        for block in blocks:
            if 'Text' in block and block['BlockType'] == "LINE":
                detected_texts.append(block['Text'])

        # If response contains a next token, update pagination token
        if 'NextToken' in response:
            pagination_token = response['NextToken']
        else:
            finished = True

    return ' '.join(detected_texts)


def process_sync_text_detection(textract_client, bucket, document):
    response = textract_client.detect_document_text(
        Document={'S3Object': {'Bucket': bucket, 'Name': document}})

    text = get_text(response)
    return text


def process_async_text_detection(textract_client, bucket, document, request_id, sns_topic_arn, sns_publishing_role_arn):
    response = textract_client.start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': document}},
        ClientRequestToken=request_id,
        NotificationChannel={
            'SNSTopicArn': sns_topic_arn,
            'RoleArn': sns_publishing_role_arn
        }
    )

    # text = get_text(response)
    return response


def lambda_handler(event, context):
    session = boto3.Session()
    textract_client = session.client('textract')

    job_id = event["JOB_ID"] if "JOB_ID" in event else ''
    # text = process_sync_text_detection(textract_client, bucket, document)

    if not job_id:
        document = event["S3_FILE_NAME"]
        bucket = event["S3_BUCKET_NAME"]
        request_id = str(round(time.time())) if context.aws_request_id is None else context.aws_request_id
        sns_topic_arn = event["SNS_TOPIC_ARN"]
        sns_publishing_role_arn = event["SNS_PUBLISHING_ROLE_ARN"]

        print(f'sending to textract {bucket}/{document} with {request_id}')
        response = process_async_text_detection(
            textract_client,
            bucket,
            document,
            request_id,
            sns_topic_arn,
            sns_publishing_role_arn
        )
        print(response)
        return response

    print(f'retrieving result : {job_id}')
    response = get_result(textract_client, job_id)
    print(response)
    return response


if __name__ == "__main__":
    class Context(dict):
        aws_request_id = str(round(time.time()))
        pass


    context = Context()

    lambda_handler({
        "S3_FILE_NAME": os.environ['S3_FILE_NAME'],
        "S3_BUCKET_NAME": os.environ['S3_BUCKET_NAME'],
        "SNS_PUBLISHING_ROLE_ARN": os.environ['SNS_PUBLISHING_ROLE_ARN'],
        "SNS_TOPIC_ARN": os.environ['SNS_TOPIC_ARN'],
        "JOB_ID": os.environ['JOB_ID']
    }, context)
