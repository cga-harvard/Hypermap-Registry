from dynasty.models import Dynasty
import re


def year_miner(text):
    date = None
    try:
        year = re.search('\d{2,4} ?B?CE', text)
        bc_year = re.search('\d{2,4} ?BC', text)
    except:
        pass
    if year:
        # we get the year numeric as a string object
        year_str = str(int(filter(str.isdigit, str(year.group(0)))))
        if "CE" in year.group(0):
            date = str(year_str.zfill(4))+'-01'+'-01'
        if "BCE" in year.group(0):
            date = str('-'+str(year_str).zfill(4))+'-01'+'-01'
    if bc_year:
        bc_year_str = str(int(filter(str.isdigit, str(bc_year.group(0)))))
        if "BC" in bc_year.group(0):
            date = str('-'+str(bc_year_str).zfill(4))+'-01'+'-01'
    return date


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
    text = text.decode("utf-8")
    date = None
    dates = []
    try:
        years = re.findall(r'\d+', text)
    except:
        pass
    if years:
        dates = valid_dates(years)
    if dynasty_miner(text):
        dates.append(dynasty_miner(text))
    if year_miner(text):
        if date:
            dates.remove(date)
        dates.append(year_miner(text))
    if dates:
        date = dates
    return date
