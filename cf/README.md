# use pip

```
export LD_LIBRARY_PATH=/app/.heroku/python/lib/
export PATH=/app/.heroku/python/bin:/bin:/usr/bin
```

# if restart app changes in site packages will be lost
```
cf restart APP-NAME
```