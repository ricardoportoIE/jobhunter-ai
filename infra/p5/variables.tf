variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the explicitly selected AWS account."
  }
}
variable "session_id" {
  type = string
  validation {
    condition     = can(regex("^p5-[a-z0-9]{12}$", var.session_id))
    error_message = "Use a controller-generated session ID."
  }
}
variable "ami_id" {
  type = string
  validation {
    condition     = can(regex("^ami-[a-f0-9]{17}$", var.ami_id))
    error_message = "Pin an Amazon Linux 2023 x86_64 AMI for this session."
  }
}
variable "expires_at" {
  type = string
  validation {
    condition     = can(formatdate("YYYY-MM-DD'T'hh:mm:ss", var.expires_at))
    error_message = "Use an explicit UTC termination time."
  }
}
variable "bundle_path" { type = string }
variable "bundle_sha256" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.bundle_sha256))
    error_message = "The source bundle must have a SHA-256 digest."
  }
}
variable "compose_version" { type = string }
variable "compose_sha256" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.compose_sha256))
    error_message = "Pin the verified Docker Compose Linux x86_64 binary digest."
  }
}
