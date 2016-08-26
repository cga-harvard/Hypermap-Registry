DEV_DOCKER_FILES=-f docker-compose.yml -f docker-compose.override.yml

ifndef DOCKER_FILES
    DOCKER_FILES=$(DEV_DOCKER_FILES)
endif

DOCKER_COMPOSE=docker-compose $(DOCKER_FILES)
TEST_FLAGS=-e REGISTRY_SKIP_CELERY=True

pre-up:
	# Bring up the database and rabbitmq first
	$(DOCKER_COMPOSE) up -d postgres rabbitmq

wait:
	sleep 2


up:
	# Bring up the rest of the services
	$(DOCKER_COMPOSE) up -d --remove-orphans

build:
	$(DOCKER_COMPOSE) build django
	$(DOCKER_COMPOSE) build celery

sync: pre-up wait
	# set up the database tables
	$(DOCKER_COMPOSE) run django python manage.py migrate --noinput
	# load the default catalog and users (hypermap)
	$(DOCKER_COMPOSE) run django python manage.py loaddata \
	            hypermap/aggregator/fixtures/catalog_default.json \
	            hypermap/aggregator/fixtures/user.json

logs:
	$(DOCKER_COMPOSE) logs --follow

down:
	$(DOCKER_COMPOSE) down --remove-orphans

test-unit: DOCKER_FILES=$(DEV_DOCKER_FILES)
test-unit:
	$(DOCKER_COMPOSE) run $(TEST_FLAGS) django python manage.py test hypermap.aggregator --failfast

test-solr: DOCKER_FILES=-$(DEV_DOCKER_FILES) -f docker-compose.solr.yml
test-solr:
	# Run tests API <--> Solr backend
	$(DOCKER_COMPOSE) run $(TEST_FLAGS) django python manage.py test hypermap.search_api --failfast

test-elastic: DOCKER_FILES=$(DEV_DOCKER_FILES) -f docker-compose.elasticsearch.yml
test-elastic:
	# Run tests API <--> Elastic backend
	$(DOCKER_COMPOSE) run $(TEST_FLAGS) django python manage.py test hypermap.search_api --failfast

test: down start test-unit test-solr test-elastic

shell: $(DOCKER_COMPOSE) run django python manage.py shell_plus

# TODO: make it reset db ONLY with explicit indications. now: down/up db cleanup. future: down/up continue working on.
start: sync up

restart: down start

pull:
	$(DOCKER_COMPOSE) pull

reset: pull build restart

flake:
	flake8 hypermap --ignore=E121,E123,E126,E226,E24,E704,W503,W504


.PHONY: pre-up wait up build sync logs down test-unit test-search test-solr test-elastic test shell start restart pull reset flake
