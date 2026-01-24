# MacBook DevOps Role

Роль для автоматической настройки DevOps-окружения на macOS (ARM64/x86_64).

## Что устанавливается

### Инструменты (через Homebrew):
- **kubectl** - управление Kubernetes кластерами
- **helm** - пакетный менеджер для Kubernetes
- **terraform** - Infrastructure as Code
- **k3d** - локальный Kubernetes (на базе Docker)

### Сервисы (в Docker контейнерах):
- **Redis** - база данных in-memory (порт 6379)
- **PostgreSQL** - реляционная БД (порт 5433)
- **Gitea** - Git сервер (HTTP: 3000, SSH: 2222)
- **Prometheus** - мониторинг (порт 9090)
- **Grafana** - дашборды для мониторинга (порт 3001)

### K3s кластер:
- **1 сервер + 2 агента**
- Доступ через kubectl (автоматически настроен)
- LoadBalancer на порту 8080

## Использование

### Запустить роль на MacBook:

```bash
# Из корня ansible репозитория
ansible-playbook playbooks/setup-macbook.yml
```

### Доступ к сервисам:

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| Grafana | http://localhost:3001 | admin/admin123 |
| Gitea | http://localhost:3000 | настроить при первом входе |
| Prometheus | http://localhost:9090 | - |
| PostgreSQL | localhost:5433 | devops/devops123 |
| Redis | localhost:6379 | - |

### Управление K3s кластером:

```bash
# Статус кластера
kubectl cluster-info
kubectl get nodes

# Просмотреть все поды
kubectl get pods -A

# Применить манифест
kubectl apply -f deployment.yaml
```

### Управление Docker Compose стеком:

```bash
# Перейти в директорию
cd ~/code/devops

# Статус
docker-compose ps

# Логи
docker-compose logs -f [service_name]

# Остановить
docker-compose down

# Перезапустить
docker-compose restart [service_name]
```

### Полезные скрипты:

```bash
# Статус всей DevOps инфры
~/code/devops/scripts/devops-status.sh

# Переключить Kubernetes контекст
~/code/devops/scripts/k8s-context.sh <context-name>

# Запустить K3s кластер
~/code/devops/scripts/k3s-start.sh

# Остановить K3s кластер
~/code/devops/scripts/k3s-stop.sh
```

## Структура файлов

```
~/code/devops/                   # Главная DevOps директория
├── docker-compose.yml           # Docker Compose конфиг
├── prometheus/
│   └── prometheus.yml          # Конфиг Prometheus
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── prometheus.yml  # Автоматический datasource
├── data/                        # Данные сервисов
│   ├── redis/
│   ├── postgres/
│   ├── gitea/
│   ├── prometheus/
│   └── grafana/
├── terraform/                   # Terraform проекты
├── kubernetes/                  # K8s манифесты
└── scripts/                     # Полезные скрипты
    ├── k8s-context.sh          # Переключение k8s контекста
    ├── devops-status.sh        # Статус всей инфры
    ├── k3s-start.sh            # Запуск K3s кластера
    └── k3s-stop.sh             # Остановка K3s кластера
```

**Важно:** Ansible управляет инфраструктурой, а все DevOps файлы - в `~/code/devops`!

## Переменные

Основные переменные в `defaults/main.yml`:

```yaml
# Главная DevOps директория (в ~/code/devops)
macbook_devops_dir: "~/code/devops"

macbook_devops_ports:                       # Порты сервисов
  postgres: 5433
  gitea_http: 3000
  grafana: 3001
  prometheus: 9090
  redis: 6379

macbook_k3d_cluster_name: "devops"          # Название K3s кластера
macbook_k3d_cluster_agents: 2               # Количество агентов
```

## Переустановка на новом Mac

Роль полностью переносимая! На новом Mac:

1. Склонировать ansible репозиторий
2. Установить Ansible: `pip install ansible-core`
3. Запустить playbook: `ansible-playbook playbooks/setup-macbook.yml`

Всё будет развёрнуто точно так же.

## Следующие шаги для DevOps обучения

### Управление K3s кластером:

```bash
# Запуск кластера
~/code/devops/scripts/k3s-start.sh

# Остановка кластера
~/code/devops/scripts/k3s-stop.sh

# Удалить кластер полностью
k3d cluster delete devops

# Список всех кластеров
k3d cluster list
```

### Kubernetes практика:

1. **Kubernetes:**
   ```bash
   helm install my-app bitnami/nginx
   kubectl get pods
   ```

2. **Terraform:**
   ```bash
   cd ~/code/devops/terraform
   terraform init
   terraform apply
   ```

3. **CI/CD:**
   - Создать репозиторий в Gitea
   - Настроить GitHub/GitLab Actions Runner
   - Деплой в K3s через helm

4. **Мониторинг:**
   - Открыть Grafana
   - Импортировать dashboard (ID: 1860 для node exporter)
   - Следить за метриками

## Troubleshooting

**K3s кластер:**
```bash
# Статус кластера
k3d cluster list

# Перезапустить кластер
~/code/devops/scripts/k3s-stop.sh
~/code/devops/scripts/k3s-start.sh

# Удалить и создать заново
k3d cluster delete devops
~/code/devops/scripts/k3s-start.sh
```

**Docker контейнеры:**
```bash
cd ~/code/devops
docker-compose ps
docker-compose logs [service_name]
docker-compose restart [service_name]
```

**kubectl не видит кластер:**
```bash
export KUBECONFIG="$(k3d kubeconfig write devops)"
kubectl cluster-info
```
