# VPN Servers Role

## Overview
Role for setting up and managing VPN servers using Docker containers. Supports multiple VPN protocols and provides comprehensive security features.

## Features
- Multi-protocol VPN support (3x-ui/Xray, AmnesiaWG)
- Automatic SSL certificate management with Certbot
- Firewall configuration with iptables
- Fail2ban integration for security
- Docker-based deployment
- Subscription system for VPN configurations

## Requirements
- Ansible 2.9+
- Docker and docker-compose on target servers
- SSH access to target servers
- Tested on Ubuntu 20.04/22.04 and Debian 12

## Role Variables

### Required Variables (vars/secrets.yml)
- `panel_username`: Admin username for 3x-ui panel
- `panel_password`: Admin password for 3x-ui panel
- `amneziawg_password`: Password for AmnesiaWG admin panel
- `cloudflare_email`: Email for Cloudflare API
- `cloudflare_api_key`: API key for Cloudflare DNS management

### Optional Variables (defaults/main.yml)
- `domain_name`: Domain name for SSL certificate
- `city`: City name for configuration identification
- `update_repo`: Enable/disable repository updates (default: true)
- `force_repo_update`: Force repository updates (default: true)
- `PWD`: Base directory for installations (default: "/server")

## Dependencies
- common role (for basic server setup)
- watchtower role (for container updates)

## Example Playbook
```yaml
- hosts: vpn_servers
  roles:
    - role: vpn_servers
      vars:
        domain_name: "vpn.example.com"
        city: "amsterdam"
```