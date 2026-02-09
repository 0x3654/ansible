# GISP Role

## Description
GISP - Minpromtorg registry search system with OpenWebUI interface.

## Requirements
- Ansible 2.9+
- Docker installed on target system

## Role Variables
Available variables with defaults (see `defaults/main.yml`):

```yaml
gisp_path: "/gisp"
gisp_folder_user: "gisp"
```

### Secrets
Create `vars/secrets.yml` based on `vars/secrets.yml.example`:

```yaml
gisp_telegram_bot_token: "your_token"
gisp_telegram_chat_id: "your_chat_id"
```

## Dependencies
- `common` role

## Example Playbook

```yaml
- hosts: servers
  roles:
    - role: gisp
```

## Access
- OpenWebUI: http://server:3333
  - Default login: admin@gisp.ru / 123

## Tags
- `apt` - Package management
- `filescopy` - File copying
- `firewall` - Firewall configuration (port 3333)

## Testing
Run test playbook:
```bash
ansible-playbook tests/test.yml
```
