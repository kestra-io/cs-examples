terraform {
  backend "gcs" {
    bucket = "kestra-managed-vm-assets"
  }
}
