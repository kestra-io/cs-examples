resource "google_compute_firewall" "allow_rdp" {
  name    = "allow-rdp-my-laptop"
  network = "{{ inputs.network }}"
  project = "{{ inputs.billingAccount }}"

  allow {
    protocol = "tcp"
    ports    = ["3389", "53", "88", "135", "389", "445", "464", "5985", "5986"]
  }

  allow {
    protocol = "udp"
    ports    = ["53", "88", "389", "464", "123"]
  }

  allow {
    protocol = "icmp" # Allow Ping
  }

  # REPLACE THIS with your actual Public IP + /32
  source_ranges = ["{{ inputs.remoteUserIpAddress}}/32", "{{ inputs.subnetCIDR }}"]

  target_tags = ["rdp-enabled"]
}

resource "google_compute_instance" "ad_dc" {
  name         = "{{ inputs.vmName }}"
  machine_type = "{{ inputs.vmSize }}"
  zone         = "{{ inputs.zone }}"
  project      = "{{ inputs.billingAccount }}"
  tags         = ["rdp-enabled"]

  boot_disk {
    initialize_params {
      image = "{{ inputs.osFlavor }}"
      size  = 50
    }
  }

  network_interface {
    network            = "{{ inputs.network }}"
    subnetwork         = "{{ inputs.subnet }}"
    subnetwork_project = "{{ inputs.billingAccount }}"

    # IMPORTANT: Set this to a static IP in your subnet range (e.g., 10.128.0.5)
    # You will use this IP as the DNS server for your Ubuntu VM.
    network_ip = "{{ inputs.ipAddress }}"

    access_config {
      # Ephemeral Public IP for RDP access
    }
  }

  # This metadata script handles the Domain Controller promotion automatically
  metadata = {
    windows-startup-script-ps1 = file("${path.module}/setup-dc.ps1")
  }

  service_account {
    # It is good practice to give the VM limited scope
    scopes = ["cloud-platform"]
  }
}

output "dc_internal_ip" {
  value       = google_compute_instance.ad_dc.network_interface[0].network_ip
  description = "The internal IP to use as DNS server on Ubuntu"
}

output "external_ip" {
  value       = google_compute_instance.ad_dc.network_interface[0].access_config[0].nat_ip
  description = "The external IP address of the VM"
}
