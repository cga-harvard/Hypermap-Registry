## Introduction

HHypermap (Harvard Hypermap) Registry is a platform that manages OWS, Esri REST, and other types of map service     harvesting, and orchestration and maintains uptime statistics for services and layers. Where possible, layers will  be cached by MapProxy. It is anticipated that other types of OGC service such as WFS, WCS, WPS, as well as flavors  of Esri REST and other web-GIS protocols will eventually be included. The platform is initially being developed to  collect and organize map services for Harvard WorldMap, but there is no dependency on WorldMap. HHypermap Registry  publishes to HHypermap Search (based on Lucene) which provides a fast search and visualization environment for spatio-temporal materials. The initial funding for HHypermap Registry came from a grant to the Center for Geographic Analysis (CGA) from the National Endowment for the Humanities.

CGA maintains a live instance of HHypermap at this url: http://hh.worldmap.harvard.edu

A description of the HHypermap API is here: http://hh.worldmap.harvard.edu/registry/api/docs/. The documentation for the API still needs to be fleshed out with examples for how to get a heatmap, what the values mean, how to get a temporal histogram, how to search using special characters like *, etc.

It is possible to install a local instance of HHypermap following the [installation instructions](developers.md)

## Sections

[Users documentation](users.md): For people who use Registry via the UI

[Admins documentation](admins.md): For people who configure Registry for others to use.

[Developers documentation](developers.md): For people who develop Registry.
