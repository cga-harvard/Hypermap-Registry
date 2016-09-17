# Hhypermap registry troubleshootings

**1. When I add an url into the database, services are not created**

  - Verify that database service is ready with migrations.
  - Check that celery process started after database migrations.

**2. Services and layers are created, but layers are not indexed into search backend**

As an administrator, verify in the *periodic tasks* section that index cached layers task is set.

![](https://cloud.githubusercontent.com/assets/54999/18128944/f18219f0-6f4d-11e6-98d3-6dab0a2a37d9.png)