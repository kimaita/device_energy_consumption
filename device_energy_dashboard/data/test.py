from data.api import API, date_to_bounds
from datetime import datetime as dt, timedelta

if __name__ == '__main__':

   yesterday = dt.today() - timedelta(days=1)
   week_ago = dt.today() - timedelta(weeks=1)


   api = API()
   reading_today = api.getReadingsInDay()
   readings_yday = api.getReadingsInDay(yesterday)
   readings_pastweek = api.getReadingsInPeriod(week_ago, dt.today())
   
   print(f"Readings today: {reading_today.shape}")
   print(reading_today.head())
   print(f"Readings yesterday {yesterday}: {len(readings_yday)}")
   print(f"Readings over week since {week_ago}: {len(readings_pastweek)}")
   readings_pastweek.info()
