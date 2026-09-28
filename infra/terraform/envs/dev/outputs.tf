output "launchpad" {
  description = "Resource names created by the LaunchPad module"
  value       = module.launchpad
}

output "cicd" {
  description = "Cloud Build service account and triggers"
  value       = module.cicd
}
