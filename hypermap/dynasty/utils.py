# -*- coding: utf-8 -*-

from hypermap.dynasty.models import Dynasty
import re


def get_mined_dates(text):
    mined_dates = []
    dates = mine_date(text)
    if dates:
        for date in dates:
            if isinstance(date, list):
                for range_date in date:
                    mined_dates.append(range_date)
                    # TODO here we need to detect first date and last date
            else:
                mined_dates.append(date)
    # we remove duplicates
    mined_dates = list(set(mined_dates))
    return mined_dates


def clean_text(text):
    try:
        text = text.decode("utf-8")
    except UnicodeEncodeError:
        text = text.encode("ascii", "ignore")
    except:
        pass
    return text


def year_miner(text):
    dates = []
    try:
        years = re.findall('\d{2,4} ?B?CE', text)
        bc_years = re.findall('\d{2,4} ?BC', text)
    except:
        pass
    if bc_years:
        for bc_year in bc_years:
            if "BC" in bc_year:
                bc_year = re.findall('\d+', bc_year)[0]
                bcdate = str('-'+str(bc_year).zfill(4))+'-01'+'-01'
                dates.append(bcdate)
    if years:
        for year in years:
            if "CE" in year and "BCE" not in year:
                year = re.findall('\d+', year)[0]
                cedate = str(year.zfill(4))+'-01'+'-01'
                dates.append(cedate)
            if "BCE" in year and bc_years is None:
                year = re.findall('\d+', year)[0]
                bcedate = str('-'+str(year).zfill(4))+'-01'+'-01'
                dates.append(bcedate)
    return dates


def dynasty_miner(text):
    date_range = None
    dates = []
    dynasties = Dynasty.objects.values_list('name', flat=True)
    word_set = set(dynasties)
    text_set = set(text.split())
    common_set = None
    if word_set.intersection(text_set):
        common_set = word_set.intersection(text_set)
    if common_set:
        for item in common_set:
            date_range = Dynasty.objects.get(name=item).date_range
    if date_range:
        years = re.findall('[-\d]+', date_range)
        for year in years:
            if year.startswith('-'):
                year = year[1:]
                date = str('-'+str(year).zfill(4))+'-01'+'-01'
            else:
                date = str(str(year).zfill(4))+'-01'+'-01'
            dates.append(date)
    return dates


def valid_dates(years):
    valid_years = []
    for year in years:
        if len(year) <= 4 and int(year) >= 1400:
            date = str(year+'-01'+'-01')
            valid_years.append(date)
    return valid_years


def mine_date(text):
    text = clean_text(text)
    date = None
    dates = []
    try:
        years = re.findall(r'\d+', text)
    except:
        pass
    if dynasty_miner(text):
        dates.append(dynasty_miner(text))
    if year_miner(text):
        if date:
            dates.remove(date)
        dates.append(year_miner(text))
    if years and not year_miner(text):
        for years in valid_dates(years):
            dates.append(years)
    if dates:
        date = dates
    return date
