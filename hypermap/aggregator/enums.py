SERVICE_TYPES = (
    ('WM', 'Harvard WorldMap'),
    ('OGC_WMS', 'Web Map Service (WMS)'),
    ('OGC_WMTS', 'Web Map Tile Service (WMTS)'),
    ('OGC_TMS', 'Tile Map Service (TMS)'),
    ('ESRI_MapServer', 'ArcGIS REST MapServer'),
    ('ESRI_ImageServer', 'ArcGIS REST ImageServer'),
    ('WARPER', 'Mapwarper'),
)

DATE_DETECTED = 0
DATE_FROM_METADATA = 1

DATE_TYPES = (
    (DATE_DETECTED, 'Detected'),
    (DATE_FROM_METADATA, 'From Metadata'),
)
