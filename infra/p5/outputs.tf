output "instance_id" { value = aws_instance.demo.id }
output "bucket" { value = aws_s3_bucket.session.id }
output "session_id" { value = var.session_id }
output "expires_at" { value = var.expires_at }
output "region" { value = "eu-west-1" }
output "account_id" { value = var.account_id }
output "log_group" { value = aws_cloudwatch_log_group.demo.name }
