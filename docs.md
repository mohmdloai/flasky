###### Stop all services

```bash
docker-compose down
```

###### Remove old celery beat schedule files

```bash
rm celerybeat-schedule*

```

###### Rebuild and start

```bash
docker-compose up --build -d
```

###### Check if tasks are registered

```bash
docker-compose exec celery-worker celery -A celery_worker.celery inspect registered
```

```bash
---->Flask API: http://localhost:3000
---->RabbitMQ Management: http://localhost:15672 (admin/admin)
---->Flower (Celery monitoring): http://localhost:5555
---->Redis: localhost:6379
```

###### structure of files

```bash
##-->files tree:
flasky/
├── app/
│   ├── __init__.py
│   ├── celery_app.py
│   ├── tasks.py
│   ├── routes.py
│   ├── models.py
│   └── helper.py
├── app.py
├── celery_worker.py       ← ← workers
├── config.py
├── docker-compose.yml
├── requirements.txt
└── Dockerfile
└── ...etc


```

#### Check worker logs

```bash
docker-compose logs -f celery-worker
```

##### Check beat logs

```bash
docker-compose logs -f celery-beat
```

#### Test Task Registration:

```bash
# List registered tasks
docker-compose exec celery-worker celery -A celery_worker.celery inspect registered
```

#### How can i see data in redis? ← Redis CLI

```bash
# Connect to Redis container
docker exec -it flasky-redis redis-cli

# Once inside, you can run Redis commands:
# List all keys
KEYS *

# Get specific key value
GET low_stock_products
GET popular_products
GET "sales_report:2025-01-15"

# Get all keys matching a pattern
KEYS sales_report:*

# View key type
TYPE low_stock_products

# View key with TTL (time to live)
TTL low_stock_products

# Exit Redis CLI
exit
```



##### some git commands i need to use:

```bash
 git log --pretty=format:"%h %s"
```

```bash
# display the full commit message (subject and body)
 git log --pretty=format:"%B"
```
##### Hints :

```bash
%h -> represents the abbreviated commit hash.
%s -> represents the subject (first line) of the commit message.
%b -> represents the body of the commit message.
%B -> represents the full raw commit message (subject and body).