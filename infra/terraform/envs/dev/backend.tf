# State bucket is created once by hand:
#   gcloud storage buckets create gs://project-3e77a7b7-cc39-467f-8a8-tfstate --location=us-east1 \
#     --uniform-bucket-level-access --public-access-prevention
#   gcloud storage buckets update gs://project-3e77a7b7-cc39-467f-8a8-tfstate --versioning
terraform {
  backend "gcs" {
    bucket = "project-3e77a7b7-cc39-467f-8a8-tfstate"
    prefix = "firewatch/dev"
  }
}
