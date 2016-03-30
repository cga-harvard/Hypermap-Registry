from dynasty.models import Dynasty
import re
from dateutil.parser import parse

def worldmap_date_miner(text):
    date = None
    try:
        year = re.search('\d{2,4} ?B?CE', text)
    except:
        pass
    if year:
        # we get the year numeric as a string object
        year_str = str(int(filter(str.isdigit, str(year.group(0)))))
        if "CE" in year.group(0):
            date = str(year_str.zfill(4))+'-01'+'-01'
        if "BCE" in year.group(0):
            date = str('-'+year_str.zfill(4))+'-01'+'-01'
    return date

def dynasty_miner(text):
    date_range = None
    dynasties = Dynasty.objects.values_list('name', flat=True)
    word_set = set(dynasties)
    text_set = set(text.split())
    common_set = None
    if word_set.intersection(text_set):
        common_set = word_set.intersection(text_set)
    if common_set:
        for item in common_set:
            date_range = Dynasty.objects.get(name=item).date_range
    return date_range

def mine_date(text):
    text = text.decode("utf-8")
    date = None
    dates = []
    try:
        year = re.search('(?:^|\D)(\d{4})(?=$|\D)', text)
    except:
        pass
    if year:
        date = parse(str(year.group(1)+'-01'+'-01'))
        dates.append(date)
    if dynasty_miner(text):
        dates.append(dynasty_miner(text))
    if worldmap_date_miner(text):
        dates.append(worldmap_date_miner(text))
    if dates:
        date = dates 
    return date
