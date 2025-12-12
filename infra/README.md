## Plan
- Use Terraform/Terragrunt to define the AWS components required to:
  - Run an **EC2 GPU instance** for Ollama (open-source model backend)
  - Access the instance via **SSM only** (no inbound ports, no public API exposure)
  - Enforce a **start always includes auto-stop** safety gate via only spinning up with a lamda that also includes scheduled shutdown or something

## Core AWS pieces
- Networking: VPC + subnet + route table + IGW (for outbound HTTPS only)
- Security group: **no ingress at all**, outbound allowed
- IAM:
  - EC2 instance profile with `AmazonSSMManagedInstanceCore`
  - Bedrock invoke permissions (optional, when you run agent on AWS)
- Cost guardrail:
  - Lambda `StartGpuInstance` starts EC2 and creates a one-off EventBridge Scheduler job
  - Lambda `StopGpuInstance` stops EC2 (also used by the schedule)
- IAM restriction for your human identity:
  - cannot call `ec2:StartInstances` directly; can only invoke the start/stop Lambdas

## Notes
- Terraform state is stored remotely (core backend already exists in another repo).
- This repo focuses on application-specific infra