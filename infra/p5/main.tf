locals {
  name = "jobhunter-${var.session_id}"
  tags = {
    Project   = "jobhunter-ai"
    Phase     = "P5"
    Session   = var.session_id
    ExpiresAt = var.expires_at
    DataClass = "synthetic"
  }
}

resource "aws_vpc" "demo" {
  cidr_block           = "10.83.0.0/24"
  enable_dns_support   = true
  enable_dns_hostnames = true
}
resource "aws_subnet" "demo" {
  vpc_id                  = aws_vpc.demo.id
  cidr_block              = "10.83.0.0/26"
  map_public_ip_on_launch = false
}
resource "aws_internet_gateway" "demo" { vpc_id = aws_vpc.demo.id }
resource "aws_route_table" "demo" {
  vpc_id = aws_vpc.demo.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.demo.id
  }
}
resource "aws_route_table_association" "demo" {
  subnet_id      = aws_subnet.demo.id
  route_table_id = aws_route_table.demo.id
}
resource "aws_security_group" "demo" {
  name        = local.name
  description = "No inbound access; administration uses SSM."
  vpc_id      = aws_vpc.demo.id
  ingress     = []
  egress {
    description = "HTTPS package downloads and AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "session" {
  bucket        = "${local.name}-${var.account_id}"
  force_destroy = true # Only this isolated, synthetic session bucket belongs to the state.
}
resource "aws_s3_bucket_public_access_block" "session" {
  bucket                  = aws_s3_bucket.session.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "session" {
  bucket = aws_s3_bucket.session.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "session" {
  bucket = aws_s3_bucket.session.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny", Principal = "*", Action = "s3:*"
      Resource  = [aws_s3_bucket.session.arn, "${aws_s3_bucket.session.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}
resource "aws_s3_object" "bundle" {
  bucket      = aws_s3_bucket.session.id
  key         = "source/${var.bundle_sha256}.tar.gz"
  source      = var.bundle_path
  source_hash = var.bundle_sha256
  depends_on  = [aws_s3_bucket_public_access_block.session, aws_s3_bucket_server_side_encryption_configuration.session]
}

resource "aws_iam_role" "host" {
  name                 = "${local.name}-host"
  permissions_boundary = "arn:aws:iam::aws:policy/PowerUserAccess"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.host.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "host" {
  name = "session-artefacts"
  role = aws_iam_role.host.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.session.arn}/source/*" },
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject"], Resource = "${aws_s3_bucket.session.arn}/backup/*" },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.demo.arn}:*" },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*", Condition = { StringEquals = { "cloudwatch:namespace" = "JobHunter/P5" } } }
    ]
  })
}
resource "aws_iam_instance_profile" "host" {
  name = "${local.name}-host"
  role = aws_iam_role.host.name
}
resource "aws_iam_role" "expiry" {
  name                 = "${local.name}-expiry"
  permissions_boundary = "arn:aws:iam::aws:policy/PowerUserAccess"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Principal = { Service = "scheduler.amazonaws.com" }, Action = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id }, ArnLike = { "aws:SourceArn" = "arn:aws:scheduler:eu-west-1:${var.account_id}:schedule-group/default" } }
    }]
  })
}
resource "aws_iam_role_policy" "expiry" {
  role = aws_iam_role.expiry.id
  name = "terminate-this-session"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = "ec2:TerminateInstances", Resource = "arn:aws:ec2:eu-west-1:${var.account_id}:instance/*"
      Condition = { StringEquals = { "ec2:ResourceTag/Session" = var.session_id, "ec2:ResourceTag/Project" = "jobhunter-ai" } }
    }]
  })
}

resource "aws_cloudwatch_log_group" "demo" {
  name              = "/jobhunter/p5/${var.session_id}"
  retention_in_days = 1
}
resource "aws_cloudwatch_metric_alarm" "health" {
  alarm_name          = local.name
  namespace           = "JobHunter/P5"
  metric_name         = "Ready"
  dimensions          = { Session = var.session_id }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_description   = "Private demo readiness or heartbeat missing; inspect SSM."
}

resource "aws_instance" "demo" {
  ami                                  = var.ami_id
  instance_type                        = "t3.medium"
  subnet_id                            = aws_subnet.demo.id
  vpc_security_group_ids               = [aws_security_group.demo.id]
  associate_public_ip_address          = true
  iam_instance_profile                 = aws_iam_instance_profile.host.name
  instance_initiated_shutdown_behavior = "terminate"
  user_data_replace_on_change          = true
  monitoring                           = false
  credit_specification { cpu_credits = "standard" }
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 24
    encrypted             = true
    delete_on_termination = true
    tags                  = local.tags
  }
  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", {
    expires_at      = var.expires_at
    bucket          = aws_s3_bucket.session.id
    bundle_key      = aws_s3_object.bundle.key
    bundle_sha256   = var.bundle_sha256
    session_id      = var.session_id
    compose_version = var.compose_version
    compose_sha256  = var.compose_sha256
  })
  depends_on = [aws_iam_role_policy_attachment.ssm, aws_iam_role_policy.host, aws_iam_role_policy.expiry, aws_route_table_association.demo]
  lifecycle {
    precondition {
      condition     = timecmp(var.expires_at, timestamp()) > 0 && timecmp(var.expires_at, timeadd(timestamp(), "8h")) <= 0
      error_message = "The session must end in the next eight hours."
    }
  }
}
resource "aws_scheduler_schedule" "expiry" {
  name                         = local.name
  schedule_expression          = "at(${formatdate("YYYY-MM-DD'T'hh:mm:ss", var.expires_at)})"
  schedule_expression_timezone = "UTC"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances"
    role_arn = aws_iam_role.expiry.arn
    input    = jsonencode({ InstanceIds = [aws_instance.demo.id] })
    retry_policy {
      maximum_event_age_in_seconds = 300
      maximum_retry_attempts       = 3
    }
  }
  depends_on = [aws_iam_role_policy.expiry]
}
