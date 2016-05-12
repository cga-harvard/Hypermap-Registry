SERVICE_TYPES = (
    ('WM', 'Harvard WorldMap'),
    ('OGC:WMS', 'Web Map Service (WMS)'),
    ('OGC:WMTS', 'Web Map Tile Service (WMTS)'),
    ('OGC:TMS', 'Tile Map Service (TMS)'),
    ('ESRI:ArcGIS:MapServer', 'ArcGIS REST MapServer'),
    ('ESRI:ArcGIS:ImageServer', 'ArcGIS REST ImageServer'),
    ('WARPER', 'Mapwarper'),
)

DATE_DETECTED = 0
DATE_FROM_METADATA = 1

DATE_TYPES = (
    (DATE_DETECTED, 'Detected'),
    (DATE_FROM_METADATA, 'From Metadata'),
)
