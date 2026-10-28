resource "google_compute_instance" "default" {
  name         = "{{ inputs.vmName }}"
  machine_type = "{{ inputs.vmSize }}"
  zone         = "{{ inputs.zone }}"
  project      = "{{ inputs.billingAccount }}"

  boot_disk {
    initialize_params {
      image = "{{ inputs.osFlavor }}"
    }
  }

  network_interface {
    network            = "{{ inputs.network }}"
    subnetwork         = "{{ inputs.subnet }}"
    subnetwork_project = "{{ inputs.billingAccount }}"
    access_config {}
    network_ip = "{{ inputs.ipAddress }}"
  }

  metadata = {
    enable-oslogin = false
    "ssh-keys"     = <<EOT
      root:{{ secret('SSH_PUB_KEY') }}
     EOT
  }


}
output "external_ip" {
  value       = google_compute_instance.default.network_interface[0].access_config[0].nat_ip
  description = "The external IP address of the VM"
}
