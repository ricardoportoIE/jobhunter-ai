mock_provider "aws" {}

variables {
  account_id      = "123456789012"
  session_id      = "p5-abcdef123456"
  ami_id          = "ami-0123456789abcdef0"
  expires_at      = timeadd(timestamp(), "2h")
  bundle_path     = "tests/synthetic-bundle.txt"
  bundle_sha256   = sha256("synthetic")
  compose_version = "v2.39.4"
  compose_sha256  = sha256("synthetic-compose")
  buildx_version  = "v0.37.1"
  buildx_sha256   = sha256("synthetic-buildx")
}

run "isolated_plan" {
  command = plan
  assert {
    condition     = length(aws_security_group.demo.ingress) == 0
    error_message = "The demo must not expose inbound ports."
  }
  assert {
    condition     = aws_instance.demo.metadata_options[0].http_tokens == "required" && aws_instance.demo.metadata_options[0].http_put_response_hop_limit == 1
    error_message = "Containers must not obtain the instance role."
  }
  assert {
    condition     = aws_instance.demo.root_block_device[0].encrypted && aws_instance.demo.root_block_device[0].delete_on_termination
    error_message = "Synthetic storage must be encrypted and disposable."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.session.block_public_policy && aws_s3_bucket_public_access_block.session.restrict_public_buckets
    error_message = "Artefacts must remain private."
  }
  assert {
    condition     = aws_instance.demo.instance_initiated_shutdown_behavior == "terminate" && aws_instance.demo.credit_specification[0].cpu_credits == "standard"
    error_message = "A stopped instance or surplus CPU credits must not retain avoidable costs."
  }
  assert {
    condition     = aws_scheduler_schedule.expiry.target[0].arn == "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances"
    error_message = "A separate AWS deadline must terminate compute."
  }
}

run "reject_session_name" {
  command = plan
  variables { session_id = "unrelated-production" }
  expect_failures = [var.session_id]
}
