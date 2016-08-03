.PHONY: hypermap
up:
	# bring up the services
	docker-compose up -d

sync:
	# set up the database tables
	docker-compose run django python manage.py migrate --noinput
	# load the default catalog (hypermap)
	docker-compose run django python manage.py loaddata hypermap/aggregator/fixtures/catalog_default.json
	# load a superuser admin / admin
	docker-compose run django python manage.py loaddata hypermap/aggregator/fixtures/user.json

logs:
	docker-compose logs --follow

.PHONY: clean
down:
	docker-compose down
