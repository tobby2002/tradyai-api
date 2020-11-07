## how to run by neo
docker-compose -f docker-compose-production.yml up -d
docker-compose -f docker-compose-production.yml stop
# docker-compose -f docker-compose-production.yml down -v

edit ./config.js
to use postgresql

adjusted the line in web/UIconfig.js


for anyone else wondering i found the answer to my question... to use pgsql with the UI or API web/routes/baseConfig.js and put credentials then in UIconfig.js change sqlite to postgresql
edit web/routes/baseConfig.js

adapter: 'postgresql'

for anyone else wondering i found the answer to my question... to use pgsql with the UI or API web/routes/baseConfig.js and put credentials then in UIconfig.js change sqlite to postgresql
edit web/routes/baseConfig.js
--> https://github.com/askmike/gekko/issues/1353
