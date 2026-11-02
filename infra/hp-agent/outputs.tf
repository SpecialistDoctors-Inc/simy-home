output "instance_id" { value = aws_instance.agent.id }
output "instance_private_ip" { value = aws_instance.agent.private_ip }
output "ssm_start_session_command" { value = "aws ssm start-session --target ${aws_instance.agent.id} --region ${var.region}" }
output "data_volume_id" { value = aws_ebs_volume.data.id }
output "artifact_bucket_name" { value = aws_s3_bucket.artifact.bucket }
output "artifact_prefix" { value = var.artifact_prefix }
output "ecr_repository_url" { value = aws_ecr_repository.agent.repository_url }
output "cloudwatch_log_group" { value = aws_cloudwatch_log_group.agent.name }
