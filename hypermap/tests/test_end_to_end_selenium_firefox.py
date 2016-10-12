# -*- coding: utf-8 -*-
import os
import re
import time
import unittest

from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from hypermap.aggregator.elasticsearch_client import ESHypermap
from hypermap.aggregator.solr import SolrHypermap

SELENIUM_HUB_URL = os.environ.get("SELENIUM_HUB_URL", None)
BROWSER_HYPERMAP_URL = os.environ.get("BROWSER_HYPERMAP_URL",
                                      "http://localhost")
BROWSER_SEARCH_URL = "{0}/_elastic".format(BROWSER_HYPERMAP_URL)
# TODO: Uncomment this when a fix for ES 6.0 with nginx is found.
#BROWSER_SEARCH_URL = "{0}/_elastic".format(BROWSER_HYPERMAP_URL)
BROWSER_SEARCH_URL = "http://elasticsearch:9200"
BROWSER_MAPLOOM_URL = "{0}/_maploom/".format(BROWSER_HYPERMAP_URL)
WAIT_FOR_CELERY_JOB_PERIOD = int(
    os.environ.get("WAIT_FOR_CELERY_JOB_PERIOD", 30))

SEARCH_TYPE = settings.REGISTRY_SEARCH_URL.split('+')[0]
SEARCH_URL = settings.REGISTRY_SEARCH_URL.split('+')[1]
SEARCH_TYPE_SOLR = 'solr'
SEARCH_TYPE_ES = 'elasticsearch'
catalog_test_slug = 'hypermap'


class TestBrowser(unittest.TestCase):
    def setUp(self):
        if not SELENIUM_HUB_URL:
            # run test on firefox of this machine.
            self.driver = webdriver.Firefox()
        else:
            # run test on stand alone node machine in docker: selenium-firefox
            self.driver = webdriver.Remote(
                command_executor=SELENIUM_HUB_URL,
                desired_capabilities=DesiredCapabilities.FIREFOX
            )
        self.driver.implicitly_wait(30)
        self.base_url = BROWSER_HYPERMAP_URL
        self.verificationErrors = []
        self.accept_next_alert = True

        print '> clearing SEARCH_URL={0}'.format(SEARCH_URL)
        if SEARCH_TYPE == SEARCH_TYPE_SOLR:
            self.solr = SolrHypermap()
            # delete solr documents
            # add the schema
            print '> updating schema'.format(SEARCH_URL)
            self.solr.update_schema(catalog=catalog_test_slug)
            self.solr.clear_solr(catalog=catalog_test_slug)

            self.search_engine_endpoint = '{0}/solr/{1}/select'.format(
                SEARCH_URL, catalog_test_slug
            )
        elif SEARCH_TYPE == SEARCH_TYPE_ES:
            es = ESHypermap()
            # delete ES documents
            es.clear_es()
            self.search_engine_endpoint = '{0}/{1}/_search'.format(
                SEARCH_URL, catalog_test_slug
            )
        else:
            raise Exception("SEARCH_TYPE not valid=%s" % SEARCH_TYPE)

    def test_browser(self):

        ENDPOINT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                     "mesonet.agron.iastate.edu.txt")

        print ""
        print ">>> with env:"
        print "REGISTRY_SKIP_CELERY: %s" % settings.REGISTRY_SKIP_CELERY
        print "REGISTRY_LIMIT_LAYERS: %s" % settings.REGISTRY_LIMIT_LAYERS
        print "REGISTRY_CHECK_PERIOD: %s" % settings.REGISTRY_CHECK_PERIOD
        print ""
        print "SELENIUM_HUB_URL: %s" % SELENIUM_HUB_URL
        print "BROWSER_HYPERMAP_URL: %s" % BROWSER_HYPERMAP_URL
        print "BROWSER_SEARCH_URL: %s" % BROWSER_SEARCH_URL
        print "BROWSER_MAPLOOM_URL: %s" % BROWSER_MAPLOOM_URL
        print "WAIT_FOR_CELERY_JOB_PERIOD: %s" % WAIT_FOR_CELERY_JOB_PERIOD
        print "ENDPOINT FILE: %s" % ENDPOINT_FILE
        print ""
        print "Starting..."

        driver = self.driver
        time.sleep(3)

        driver.get(self.base_url + "/admin/login/?next=/admin/")
        print driver.current_url
        driver.find_element_by_id("id_password").clear()
        driver.find_element_by_id("id_password").send_keys("admin")
        driver.find_element_by_id("id_username").clear()
        driver.find_element_by_id("id_username").send_keys("admin")
        driver.find_element_by_css_selector("input[type=\"submit\"]").click()
        print driver.current_url
        driver.find_element_by_link_text("Periodic tasks").click()
        print driver.current_url
        print "> assert 3 periodic tasks. means beat is alive."
        self.assertEqual("3 periodic tasks",
                         driver.find_element_by_css_selector(
                             "p.paginator").text)
        driver.find_element_by_link_text("Home").click()
        print driver.current_url
        driver.find_element_by_link_text("Endpoint lists").click()
        print driver.current_url
        driver.find_element_by_link_text("Add endpoint list").click()
        print driver.current_url
        print "> uploading Endpoint List..."
        driver.find_element_by_id("id_upload").clear()
        driver.find_element_by_id("id_upload").send_keys(ENDPOINT_FILE)
        driver.find_element_by_name("_save").click()
        print driver.current_url

        print "> waiting {0} seconds for celery do the job....".format(
            WAIT_FOR_CELERY_JOB_PERIOD
        )
        time.sleep(WAIT_FOR_CELERY_JOB_PERIOD)

        driver.find_element_by_link_text("Aggregator").click()
        time.sleep(1)
        print driver.current_url
        driver.find_element_by_link_text("Endpoints").click()
        print driver.current_url
        print "> assert Endpoint created."
        time.sleep(1)
        self.assertEqual(
            "http://mesonet.agron.iastate.edu/cgi-bin/wms/us/wwa.cgi",
            driver.find_element_by_link_text(
                "http://mesonet.agron.iastate.edu/cgi-bin/wms/us/wwa.cgi").text)
        driver.find_element_by_link_text(
            "http://mesonet.agron.iastate.edu/cgi-bin/wms/us/wwa.cgi").click()
        # self.assertEqual("1 service/s created", driver.find_element_by_id("id_message").text)
        driver.find_element_by_link_text("Endpoints").click()
        print driver.current_url
        time.sleep(1)
        driver.find_element_by_link_text("Aggregator").click()
        print driver.current_url
        time.sleep(1)
        driver.find_element_by_link_text("Services").click()
        print driver.current_url
        print "> assert 1 Service created."
        time.sleep(1)
        self.assertEqual("1 service", driver.find_element_by_css_selector(
            "p.paginator").text)
        self.assertEqual(
            "http://mesonet.agron.iastate.edu/cgi-bin/wms/us/wwa.cgi",
            driver.find_element_by_css_selector("td.field-url").text)
        driver.find_element_by_xpath(
            '//*[@id="result_list"]/tbody/tr/th/a').click()
        print driver.current_url
        print "> assert Service details."
        time.sleep(1)

        self.assertEqual("IEM NWS Warnings WMS Service",
                         driver.find_element_by_id(
                             "id_title").get_attribute("value"))

        driver.find_element_by_link_text("Services").click()
        print driver.current_url
        driver.find_element_by_link_text("Aggregator").click()
        print driver.current_url
        driver.find_element_by_link_text("Layers").click()
        print driver.current_url
        print "> assert 3 layers created."
        time.sleep(1)
        self.assertEqual("3 layers", driver.find_element_by_css_selector(
            "p.paginator").text)
        driver.get(self.base_url + "/registry/")
        print driver.current_url
        print "> go to /registry/."

        for i in range(1, 11):
            print "> try assert checks count > 0. (%i of 10)" % i
            try:
                self.assertNotEqual("0", driver.find_element_by_xpath(
                    "//td[4]").text)
                print "> found"
                break
            except AssertionError as e:
                print "> wait and reload page"
                time.sleep(10)
                driver.get(self.base_url + "/registry/")

        try:
            self.assertNotEqual("0",
                                driver.find_element_by_xpath("//td[4]").text)
        except AssertionError as e:
            self.verificationErrors.append(str(e))

        driver.get("{0}/hypermap/_count".format(BROWSER_SEARCH_URL))
        print driver.current_url
        time.sleep(2)

        for i in range(1, 11):
            print "> assert layers indexed are 3. (%i of 10)" % i
            try:
                self.assertRegexpMatches(
                    driver.find_element_by_css_selector("pre").text,
                    "^\\{\"count\":3[\\s\\S]*$")
                print "> found"
                break
            except AssertionError:
                print "> wait and reload page"
                time.sleep(10)
                driver.refresh()

        self.assertRegexpMatches(
            driver.find_element_by_css_selector("pre").text,
            "^\\{\"count\":3[\\s\\S]*$")

        driver.get(self.base_url + "/registry/")
        print driver.current_url
        driver.find_element_by_link_text(
            "IEM NWS Warnings WMS Service").click()
        print driver.current_url
        print "> remove checks."
        driver.find_element_by_name("remove").click()
        print driver.current_url
        driver.find_element_by_link_text("Home").click()
        print driver.current_url
        print "> assert checks = 0."
        self.assertEqual("0", driver.find_element_by_xpath("//td[4]").text)
        driver.find_element_by_link_text(
            "IEM NWS Warnings WMS Service").click()
        print driver.current_url
        print "> trigger check."
        driver.find_element_by_name("check").click()
        print driver.current_url
        driver.find_element_by_link_text("Home").click()
        print driver.current_url

        for i in range(1, 11):
            try:
                print "> assert checks = 1. (%i of 10)" % i
                self.assertTrue(
                    int(driver.find_element_by_xpath("//td[4]").text) > 0)
                print "> found"
                break
            except AssertionError:
                print "> wait and reload page"
                time.sleep(10)
                driver.refresh()

        driver.find_element_by_link_text(
            "IEM NWS Warnings WMS Service").click()
        print driver.current_url
        driver.find_element_by_link_text("wwa").click()
        print driver.current_url
        print "> remove checks from Layer."
        driver.find_element_by_name("remove").click()
        print driver.current_url
        print "> assert text [No checks performed so far]."
        self.assertEqual("No checks performed so far",
                         driver.find_element_by_xpath("//tr[11]/td[2]").text)
        print "> check Layer."
        driver.find_element_by_name("check").click()
        print driver.current_url

        for i in range(1, 11):
            try:
                print "> assert text [Total Checks: N>0]. (%i of 10)" % i
                src = driver.page_source
                text_found_TOTAL_CHECKS_LTE_1 = re.search(
                    r'Total Checks: (1|2|3|4|5|6|7)', src)
                self.assertNotEqual(text_found_TOTAL_CHECKS_LTE_1, None)
                print "> found"
                break
            except AssertionError:
                print "> wait and reload page"
                time.sleep(10)
                driver.get(driver.current_url)

        src = driver.page_source
        text_found_TOTAL_CHECKS_LTE_1 = re.search(
            r'Total Checks: (1|2|3|4|5|6|7)', src)
        self.assertNotEqual(text_found_TOTAL_CHECKS_LTE_1, None)

        driver.find_element_by_link_text("Home").click()
        print driver.current_url
        driver.find_element_by_link_text("Monitor").click()
        print driver.current_url
        print "> clean Search index and wait"
        driver.find_element_by_name("clear_index").click()
        print driver.current_url
        time.sleep(5)
        driver.get("{0}/hypermap/_count".format(BROWSER_SEARCH_URL))
        print driver.current_url
        print "> assert count != 3 layers"
        try:
            self.assertNotRegexpMatches(
                driver.find_element_by_css_selector("pre").text,
                "^\\{\"count\":3[\\s\\S]*$")
        except AssertionError as e:
            self.verificationErrors.append(str(e))
        driver.get(self.base_url + "/registry/")
        print driver.current_url
        print "> finish hypermap page"
        print ""

        # TODO: activate this to test maploom, now dat app looks very buggy.
        """
        print ">> start maploom"
        driver.get(BROWSER_MAPLOOM_URL)
        print driver.current_url
        print ">> open registry modal"
        driver.find_element_by_xpath(
            "//div[@id='pulldown-content']/div[2]/div/div").click()
        print ">> assert Hypermap catalog"
        time.sleep(10)
        self.assertEqual("Hypermap",
                         driver.find_element_by_xpath(
                             "//div[@id='explore']/div/nav/div/form/div/div[2]/select").text)
        print ">> assert [Showing 3 of 3 - Page 1 / 1]"
        self.assertEqual("Showing 3 of 3 - Page 1 / 1".lower(),
                         driver.find_element_by_css_selector(
                             "span.text-muted.ng-binding").text.lower())
        driver.find_element_by_id("text_search_input_exp").clear()
        print ">> search IEM"
        driver.find_element_by_id("text_search_input_exp").send_keys("IEM")
        driver.find_element_by_id("text_search_btn").click()
        time.sleep(10)
        print ">> assert [Showing 1 of 1 - Page 1 / 1]"
        self.assertEqual("Showing 1 of 1 - Page 1 / 1".lower(),
                         driver.find_element_by_css_selector(
                             "span.text-muted.ng-binding").text.lower())
        print ">> click reset"
        driver.find_element_by_name("button").click()
        time.sleep(10)
        print ">> assert [Showing 3 of 3 - Page 1 / 1]"
        self.assertEqual("Showing 3 of 3 - Page 1 / 1".lower(),
                         driver.find_element_by_css_selector(
                             "span.text-muted.ng-binding").text.lower())
        print ">> click on 3 layers to select"
        driver.find_element_by_css_selector("td.ellipsis.ng-binding").click()
        driver.find_element_by_xpath(
            "//div[@id='registry-layers']/div/div/div/div[2]/div[2]/div/table/tbody/tr[3]/td").click()
        driver.find_element_by_xpath(
            "//div[@id='registry-layers']/div/div/div/div[2]/div[2]/div/table/tbody/tr[4]/td").click()
        print ">> click on 3 layers to unselect"
        driver.find_element_by_css_selector("td.ellipsis.ng-binding").click()
        driver.find_element_by_xpath(
            "//div[@id='registry-layers']/div/div/div/div[2]/div[2]/div/table/tbody/tr[3]/td").click()
        driver.find_element_by_xpath(
            "//div[@id='registry-layers']/div/div/div/div[2]/div[2]/div/table/tbody/tr[4]/td").click()
        """

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e:
            print e
            return False
        return True

    def is_alert_present(self):
        try:
            self.driver.switch_to_alert()
        except NoAlertPresentException as e:
            print e
            return False
        return True

    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally:
            self.accept_next_alert = True

    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)
