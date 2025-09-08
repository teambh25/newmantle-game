# Setup
```
# install docker-compose
# sudo apt-get update
# sudo apt install docker.io
# sudo apt install docker-compose

git clone 
cd newmantle-game
cp .env.example .env
# write your env file
# vi .env 
chomod +x nginx-reload.sh # for nginx reload
sudo docker-compose up -d
```

- Test / flake8
```
sudo docker-compose run --rm --entrypoint "" fastapi python -m pytest
sudo docker-compose run  --rm --entrypoint "" fastapi flake8 --show-source
```