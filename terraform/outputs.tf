output "cloudfront_url" {
  description = "Your website URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "uploads_bucket_name" {
  description = "S3 bucket for PDF uploads"
  value       = aws_s3_bucket.uploads.id
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend files"
  value       = aws_s3_bucket.frontend.id
}

output "api_gateway_url" {
  description = "API Gateway endpoint"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/results"
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.results.name
}