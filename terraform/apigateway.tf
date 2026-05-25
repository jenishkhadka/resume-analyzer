# The API itself
resource "aws_api_gateway_rest_api" "main" {
  name = "${var.project_name}-api"
}

# /results resource (the URL path)
resource "aws_api_gateway_resource" "results" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "results"
}

# GET /results method
resource "aws_api_gateway_method" "get_results" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.results.id
  http_method   = "GET"
  authorization = "NONE"
}

# Connect GET /results to Lambda
resource "aws_api_gateway_integration" "get_results" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.results.id
  http_method             = aws_api_gateway_method.get_results.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.analyzer.invoke_arn
}

# Deploy the API
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  depends_on = [
    aws_api_gateway_integration.get_results
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# Stage (like a version — we call ours "prod")
resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "prod"
}