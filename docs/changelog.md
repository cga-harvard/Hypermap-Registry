# Changelog

Version 0.3.12

 - Removed dependency on pylibmc. Fixes #181.

Version 0.3.11

 - Move to Elasticsearch 1.7 compatible query syntax.

Version 0.3.10

 - CSW-T Insert support with custom <registry> tags.
 - Custom <registry> tags available in MapLoom UI.
 - Full screen MapLoom Registry modal.
 - Adaptive pagination based on available height.
 - Fixed MapProxy issues with WMS servers. workspace:name is now sent as layer name instead of name.
 - Fixed map display issues on hover for ArcGIS layers.
 - is_monitored is set to False on services uploaded via CSW-T.
 - Added users, admins and developers documentation.
 - More robust parsing of ArcGIS services url.
 - Switched to q.param and a.param instead of a_param and q_param for future compatibility with angular-search.
 - Added uuid field, requires migrations.

Version 0.3

 - Swagger API support. Deprecated CATALOGLIST.
 - Multi Catalog.
 - Docker for development.
 - Standalone third party app.

Version 0.2

 - Elasticsearch support.
 - MapLoom UI.
 - ArcGIS MapServer support.
