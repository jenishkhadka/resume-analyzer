import json
import boto3
import os
import uuid
from datetime import datetime, timezone
from pypdf import PdfReader
from io import BytesIO

# AWS clients
s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION_NAME"])
dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_REGION_NAME"])

def lambda_handler(event, context):
    """
    This function runs automatically when a PDF is uploaded to S3.
    It does 4 things:
    1. Read the PDF from S3
    2. Extract text from the PDF
    3. Send text to Bedrock (Claude) for analysis
    4. Save results to DynamoDB
    """

    # -------------------------------------------
    # STEP 1: Figure out which file was uploaded
    # -------------------------------------------
    # When S3 triggers Lambda, it tells us the bucket and file name
    if "Records" in event:
        # Triggered by S3 upload
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        file_key = event["Records"][0]["s3"]["object"]["key"]
        document_id = str(uuid.uuid4())
    else:
        # Triggered by API Gateway (fetching results)
        params = event.get("queryStringParameters") or {}
        document_id = params.get("document_id")
        if not document_id:
            return response(400, {"error": "document_id is required"})
        return get_results(document_id)

    # -------------------------------------------
    # STEP 2: Read the PDF from S3
    # -------------------------------------------
    try:
        pdf_object = s3.get_object(Bucket=bucket_name, Key=file_key)
        pdf_bytes = pdf_object["Body"].read()
    except Exception as e:
        print(f"Error reading PDF from S3: {e}")
        return response(500, {"error": "Could not read PDF from S3"})

    # -------------------------------------------
    # STEP 3: Extract text from PDF
    # -------------------------------------------
    try:
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        resume_text = ""
        for page in pdf_reader.pages:
            resume_text += page.extract_text() or ""

        if not resume_text.strip():
            return response(400, {"error": "Could not extract text from PDF"})

        # Limit text to 4000 characters to keep Bedrock costs low
        resume_text = resume_text[:4000]
    except Exception as e:
        print(f"Error extracting text: {e}")
        return response(500, {"error": "Could not extract text from PDF"})

    # -------------------------------------------
    # STEP 4: Send to Bedrock (Claude) for analysis
    # -------------------------------------------
    prompt = f"""You are an expert resume analyzer. Analyze the following resume and return a JSON response only. No extra text, just JSON.

Resume:
{resume_text}

Return this exact JSON structure:
{{
    "candidate_name": "full name from resume",
    "skills": ["skill1", "skill2", "skill3"],
    "experience_summary": "2-3 sentence summary of their experience",
    "years_of_experience": 0,
    "education": "highest education level",
    "job_match_score": 75,
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "recommended_roles": ["role1", "role2"]
}}"""

    try:
        bedrock_response = bedrock.invoke_model(
            modelId=os.environ["BEDROCK_MODEL"],
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )

        # Parse Bedrock response
        result = json.loads(bedrock_response["body"].read())
        analysis_text = result["content"][0]["text"]
        analysis = json.loads(analysis_text)

    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return response(500, {"error": "Could not analyze resume"})

    # -------------------------------------------
    # STEP 5: Save results to DynamoDB
    # -------------------------------------------
    try:
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        table.put_item(Item={
            "document_id": document_id,
            "file_name": file_key,
            "analysis": analysis,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            # Auto delete after 7 days (7 * 24 * 60 * 60 = 604800 seconds)
            "expires_at": int(datetime.now(timezone.utc).timestamp()) + 604800
        })

        print(f"Analysis saved successfully for document_id: {document_id}")
        return response(200, {
            "document_id": document_id,
            "analysis": analysis
        })

    except Exception as e:
        print(f"Error saving to DynamoDB: {e}")
        return response(500, {"error": "Could not save results"})


def get_results(document_id):
    """Fetch analysis results from DynamoDB by document_id"""
    try:
        table = dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        result = table.get_item(Key={"document_id": document_id})

        if "Item" not in result:
            return response(404, {"error": "Results not found"})

        return response(200, result["Item"])

    except Exception as e:
        print(f"Error fetching results: {e}")
        return response(500, {"error": "Could not fetch results"})


def response(status_code, body):
    """Standard API response format"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=str)
    }