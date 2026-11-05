# No launcher permissions are present until a separately reviewed validation gate
# is enabled. Presigned URLs expose only the exact input/output object keys.
resource "aws_iam_role_policy" "validation_launcher" {
  count = var.validation_enabled ? 1 : 0
  name  = "reviewed-browser-validation-only"
  role  = aws_iam_role.runtime["consumer"].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid       = "RunOnlyPinnedRendererInDedicatedCluster", Effect = "Allow", Action = ["ecs:RunTask"],
      Resource  = aws_ecs_task_definition.validation.arn,
      Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.validation.arn } }
    },
    {
      Sid      = "InspectOnlyPinnedRendererDefinition", Effect = "Allow", Action = ["ecs:DescribeTaskDefinition"],
      Resource = aws_ecs_task_definition.validation.arn
    },
    {
      Sid       = "ObserveOnlyRendererTasks", Effect = "Allow", Action = ["ecs:DescribeTasks"],
      Resource  = "arn:aws:ecs:${var.region}:209300895845:task/${aws_ecs_cluster.validation.name}/*",
      Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.validation.arn } }
    },
    {
      # ListTasks does not support resource-level IAM scoping.
      Sid       = "FindRendererTasksInDedicatedCluster", Effect = "Allow", Action = ["ecs:ListTasks"], Resource = "*",
      Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.validation.arn } }
    },
    {
      Sid       = "PassOnlyRendererExecutionRole", Effect = "Allow", Action = ["iam:PassRole"],
      Resource  = aws_iam_role.validation_execution.arn,
      Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } }
    },
    {
      Sid      = "VerifyOnlyArtifactBucketOwner", Effect = "Allow", Action = ["s3:ListBucket"],
      Resource = aws_s3_bucket.artifacts.arn
    },
    {
      Sid = "ExactRendererOutputNames", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"],
      Resource = [
        "${aws_s3_bucket.artifacts.arn}/browser-validation/*/*/*/desktop.png",
        "${aws_s3_bucket.artifacts.arn}/browser-validation/*/*/*/mobile.png",
        "${aws_s3_bucket.artifacts.arn}/browser-validation/*/*/*/report.json"
      ]
    }
  ] })
}
