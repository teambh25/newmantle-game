## Setup
```
# create environment file
cp .env.example .env
vi .env 

# make nginx reload script executable
chmod +x nginx-reload.sh

# start containers
sudo docker-compose up -d
```

## Test / Formatter
```
# run tests (pytest)
docker compose -f docker-compose.test.yml run --rm fastapi-test

# code style check & auto-fix (Ruff)
cd fastapi
ruff check --fix & ruff format 
```