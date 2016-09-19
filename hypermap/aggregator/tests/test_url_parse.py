import unittest
from hypermap.aggregator.utils import service_url_parse


class TestArcgis(unittest.TestCase):

    def test_arcgis_url_parse(self):
        urls_list = [
            'http://ags.giscenter.isu.edu/arcgis/rest/services/LiDAR/IdahoLiDAR_BareEarthModel/ImageServer/?f=json',
            'http://gis.hicentral.com/arcgis/rest/services/OperEnv/MapServer/?f=json',
            'http://services.gis.ca.gov/arcgis/rest/services/Transportation/LA_Transit/MapServer/?f=json',
            'http://gis.octa.net/ArcGIS/rest/services/ActiveTransportation/SidewalkInventory/MapServer/?f=json',
            'http://arcgis4.roktech.net/arcgis/rest/services/ReaganSmith/OK_Base_Final/MapServer/?f=json',
            'http://www.pcn.minambiente.it/arcgis/rest/services/progetti/Progetto_Incendi_PNZ/MapServer/?f=json',
            ('http://www.pcn.minambiente.it/arcgis/rest/services/progetti/Prodotti_interferometrici_ERS_descending/'
                'MapServer/?f=json'),
            'http://www.laytoncity.org/arcgis/rest/services/Basemaps/LaytonBaseMap/MapServer/?f=json',
            'http://maps.schoolsitelocator.com/arcgis/rest/services/sslJS_texas2/MapServer/?f=json',
            'http://mapserver.kgs.ku.edu/arcgis/rest/services/NG911_Imagery/NG911_Imagery_2014_SID/ImageServer/?f=json',
            'http://encdirect.noaa.gov/arcgis/rest/services/RNC/NOAA_RNC/ImageServer/?f=json',
            ('http://ngamaps.geointapps.org/arcgis/rest/services/RIO/Rio_Foundation_Transportation/MapServer/WMSServer?'
                'request=GetCapabilities&service=WMS'),
            'https://idpgis.ncep.noaa.gov/arcgis/rest/services/NWS_Observations/radar_base_reflectivity/MapServer',
            'http://mapserver.kgs.ku.edu/arcgis/rest/services/NG911_Imagery/NG911_Imagery_2014_SID/ImageServer/?f=json',
            'http://encdirect.noaa.gov/arcgis/rest/services/PrecisionNav/LA_LB_bags_image/ImageServer/?f=json',
            ('http://services.coastalresilience.org:6080/arcgis/rest/services/Future_Habitat/gulfmex_SLAMM_GCPLCC/'
                'ImageServer/?f=json'),
            'http://kgs.uky.edu/arcgis/rest/services/Hazards/LandslideInformationMap/MapServer/?f=json',
            ('http://www.pcn.minambiente.it/arcgis/rest/services/progetti/Prodotti_interferometrici_ERS_ascending/'
                'MapServer/?f=json')
        ]

        wrong_strings = ['Server', '?']

        for i, url in enumerate(urls_list):

            parsed_url = service_url_parse(url)
            for item in parsed_url:
                for wrong_string in wrong_strings:
                    self.assertFalse(wrong_string in item, 'Wrong url item found')


if __name__ == '__main__':
    unittest.main()
