output "cloudbuild_service_account" {
  value = google_service_account.cloudbuild.email
}

output "triggers" {
  value = concat(
    [for t in google_cloudbuild_trigger.agent_pr : t.name],
    [for t in google_cloudbuild_trigger.agent_deploy : "${t.name}${t.disabled ? " (disabled)" : ""}"],
    [for t in google_cloudbuild_trigger.component_pr : t.name],
  )
}
