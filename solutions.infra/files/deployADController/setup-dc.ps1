<#
.SYNOPSIS
    Automated Active Directory Domain Controller Provisioning Script.
.DESCRIPTION
    This script configures internal firewall rules, enables the NTP server (critical for Kerberos/Linux integration), 
    installs AD DS/DNS roles, and promotes a Windows Server to a Domain Controller. 
    It is designed to be idempotent and utilizes templating injection for dynamic values.
#>

# ---------------------------------------------------------
# Enable WinRM for Ansible/Kestra Integration
# ---------------------------------------------------------

# 1. Enable PowerShell Remoting (This starts the WinRM service and creates default firewall rules)
Enable-PSRemoting -Force -SkipNetworkProfileCheck

# 2. Allow Unencrypted and Basic Auth (Standard for lab environments without PKI)
Set-Item -Path WSMan:\localhost\Service\AllowUnencrypted -Value $true
Set-Item -Path WSMan:\localhost\Service\Auth\Basic -Value $true

# 3. Explicitly ensure the Windows Firewall allows 5985 and 5986 from the internal subnet
New-NetFirewallRule -DisplayName "Allow WinRM HTTP" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow -RemoteAddress $InternalSubnet
New-NetFirewallRule -DisplayName "Allow WinRM HTTPS" -Direction Inbound -LocalPort 5986 -Protocol TCP -Action Allow -RemoteAddress $InternalSubnet

# 1. Configuration Variables
# These values are injected by the automation platform at runtime.
$InternalSubnet = "{{ inputs.subnetCIDR }}"
$PasswordString = "{{ secret('AD_CONTROLLER_PW') }}"
# Convert the plaintext password to a SecureString, which is required by the AD promotion cmdlet.
$Secret = ConvertTo-SecureString $PasswordString -AsPlainText -Force

# 2. Firewall & Time Service Configuration
# Ensure the Windows Firewall allows all TCP/UDP traffic from our internal VPC subnet.
if (!(Get-NetFirewallRule -DisplayName "AD-Internal-Restricted" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "AD-Internal-Restricted" -Direction Inbound -Action Allow -Protocol TCP -LocalPort Any -RemoteAddress $InternalSubnet
    New-NetFirewallRule -DisplayName "AD-Internal-UDP-Restricted" -Direction Inbound -Action Allow -Protocol UDP -LocalPort Any -RemoteAddress $InternalSubnet
}

# Enable the Windows Time Service (W32Time) as an NTP server in the Registry.
# This is CRITICAL for Linux clients joining the domain, as Kerberos requires time drift to be under 5 minutes.
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpServer" -Name "Enabled" -Value 1

# Open UDP Port 123 in the Windows Firewall specifically for NTP traffic.
if (!(Get-NetFirewallRule -DisplayName "NTP-Inbound-UDP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "NTP-Inbound-UDP" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 123
}

# 3. Install Required Roles and Management Tools
# Check if the AD DS role is already installed to prevent unnecessary execution.
if (!(Get-WindowsFeature AD-Domain-Services).Installed) {
    # Install Active Directory, DNS, and their respective PowerShell management tools.
    Install-WindowsFeature -Name AD-Domain-Services, DNS, RSAT-DNS-Server, RSAT-AD-PowerShell -IncludeManagementTools
}

# 4. Initialize Management Modules & DNS Forwarders
# Explicitly import the DnsServer module so the cmdlets are immediately available in this session.
Import-Module DnsServer -ErrorAction SilentlyContinue
if (Get-Command Set-DnsServerForwarder -ErrorAction SilentlyContinue) {
    # Set Google DNS (8.8.8.8) as a forwarder so the DC can resolve external internet domains for clients.
    Set-DnsServerForwarder -IPAddress "8.8.8.8" -PassThru -ErrorAction SilentlyContinue
}

# 5. Active Directory Promotion Logic
# Check the WMI DomainRole property. A value of 4 (Backup DC) or 5 (Primary DC) means it's already promoted.
# This ensures the script is idempotent and won't re-run the promotion if the VM reboots.
$IsDC = (Get-WmiObject Win32_ComputerSystem).DomainRole
if ($IsDC -ne 4 -and $IsDC -ne 5) {
    
    # CRITICAL FIX for Cloud VMs: Active Directory promotion fails if the local Administrator 
    # password is blank or weak. This command forces it to match our secure password before promotion.
    net user Administrator $PasswordString
    
    # Prepare the promotion parameters using a Hash Table (Splatting) for readability and reliability.
    # Templating is used to dynamically inject and format the Domain Name and NetBIOS name.
    $ADParams = @{
        DomainName                    = "{{ inputs.domain }}"
        DomainNetbiosName             = "{{ inputs.domain | split('\.')  | first | upper }}"
        SafeModeAdministratorPassword = $Secret
        InstallDns                    = $true
        Force                         = $true
        NoRebootOnCompletion          = $false # Setting to false ensures the VM reboots automatically when done
    }

    # Load the deployment module and execute the forest promotion with our parameters.
    Import-Module ADDSDeployment
    Install-ADDSForest @ADParams
}
