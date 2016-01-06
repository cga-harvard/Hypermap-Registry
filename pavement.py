from paver.easy import sh, task

@task
def reset_db():
    """
    Reset the Django db, keeping the admin user
    """
    sh("python hypermap/manage.py sqlclear aggregator | python hypermap/manage.py dbshell")
    sh("python hypermap/manage.py syncdb")
