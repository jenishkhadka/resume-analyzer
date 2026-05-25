# ZIP the Python code so Lambda can use it
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/../lambda.zip"
}

# The Lambda function itself
resource "aws_lambda_function" "analyzer" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "${var.project_name}-analyzer"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE  = aws_dynamodb_table.results.name
      BEDROCK_MODEL   = var.bedrock_model_id
      AWS_REGION_NAME = var.aws_region
    }
  }
}

# Allow S3 to trigger Lambda
resource "aws_lambda_permission" "s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analyzer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}

# Allow API Gateway to trigger Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analyzer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}