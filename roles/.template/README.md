# {{ role_name }} Role

## Description
Brief description of what this role does.

## Requirements
- Ansible 2.9+
- Docker installed on target system

## Role Variables
Available variables with defaults (see `defaults/main.yml`):

```yaml
{{ role_name }}_domain_name: "{{ role_name }}.example.com"
{{ role_name }}_path: "/{{ role_name }}"
```

### Secrets
Create `vars/secrets.yml` based on `vars/secrets.yml.example`:

```yaml
{{ role_name }}_telegram_bot_token: "your_token"
{{ role_name }}_telegram_chat_id: "your_chat_id"
```

## Dependencies
- `common` role

## Example Playbook

```yaml
- hosts: servers
  roles:
    - role: {{ role_name }}
      vars:
        {{ role_name }}_domain_name: "myapp.example.com"
```

## Tags
- `apt` - Package management
- `filescopy` - File copying
- `firewall` - Firewall configuration
- `certbot` - SSL certificates (if applicable)

## Testing
Run test playbook:
```bash
ansible-playbook tests/test.yml
```
