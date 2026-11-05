output "base_url" { value = "https://hp-control.simy.one" }
output "authority_table" { value = aws_dynamodb_table.authority.name }
output "command_queue_url" { value = aws_sqs_queue.commands.url }
output "artifact_bucket" { value = aws_s3_bucket.artifacts.id }
output "publisher_role_arns" { value = { for env, role in aws_iam_role.publisher : env => role.arn } }
output "validation_task_definition" { value = aws_ecs_task_definition.validation.arn }
output "validation_network" {
  value = { subnet_id = aws_subnet.validation.id, security_group_id = aws_security_group.validation.id, assign_public_ip = true }
}

output "validator_config" { value = local.validator_config }

output "validator_repository_url" { value = aws_ecr_repository.validator.repository_url }
