.PHONY: hypermap
hypermap:
	cf create-service elephantsql hippo hypermap-database
	cf create-service searchly small hypermap-elasticsearch
	cf create-service cloudamqp tiger hypermap-rabbitmq
	cf cups hypermap-papertrail -l syslog://logs4.papertrailapp.com:11296
	cf push -f cf/manifest.yml

.PHONY: clean
clean:
	cf delete hypermap -f
	cf delete hypermap-celery -f
	cf delete-service hypermap-database -f
	cf delete-service hypermap-elasticsearch -f
	cf delete-service hypermap-rabbitmq -f
	cf delete-service hypermap-papertrail -f
