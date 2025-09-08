#!/bin/sh
mkdir -p certbot/conf
mkdir -p certbot/www

# 환경 변수로 conf 파일 만들기 (한번 실행해봐야됨...)
export $(xargs < .env) # 전체 환경 변수를 등록하니 조심해서 쓸것..
envsubst <./nginx/newmantle.conf.template > ./nginx/newmantle.conf

# 환경 변수로 실핼 할 수 있게 바꾸면 좋을듯...
sudo docker-compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d {server_url} --email {email}
# sudo docker-compose run --rm certbot renew # --dry-run