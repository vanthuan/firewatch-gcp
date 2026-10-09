output "firewatch" {
  description = "Resource names created by the FireWatch module"
  value       = module.firewatch
}

output "cicd" {
  description = "Cloud Build service account and triggers"
  value       = module.cicd
}
