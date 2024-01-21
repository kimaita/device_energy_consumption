from data.iot import get_devices
from data.reading import Reading

from datetime import datetime as dt
import time

from typing import List

import boto3
import pandas as pd

TABLE_NAME = 'device_energy-first'
THING_GROUP = 'device_energy_sensors'


class API:

    def __init__(self) -> None:
        """_summary_
        """
        self.iot_client = boto3.client('iot')
        self.dynamo_client = boto3.resource('dynamodb')
        self.db = Reading(self.dynamo_client)

    @property
    def iot_client(self):
        return self.__iot_client

    @iot_client.setter
    def iot_client(self, value):
        self.__iot_client = value

    @property
    def dynamo_client(self):
        return self.__dynamo_client

    @dynamo_client.setter
    def dynamo_client(self, value):
        self.__dynamo_client = value

    @property
    def db(self):
        return self.__db

    @db.setter
    def db(self, value):
        self.__db = value
        self.istableset()

    def list_to_df(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cols= lambda x: x.replace('readings.', '')
            if isinstance(result, list):
                df = pd.json_normalize(result).rename(columns=cols)
                return df
            else:
                return result
        return wrapper

    def getdevicelist(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return get_devices(self.iot_client, THING_GROUP)

    def istableset(self):
        return self.db.set_table(TABLE_NAME)

    @list_to_df
    def getReadingsInPastHrs(self, past_hours) -> List:
        """_summary_

        Returns:
            List: _description_
        """
        
        return self.db.get_latest_readings(past_hrs_millis(past_hours))
    

    @list_to_df
    def getReadingsInDay(self, date=dt.today()) -> List:
        """_summary_

        Args:
            date (_type_, optional): _description_. Defaults to dt.today().

        Returns:
            List: _description_
        """
        bounds = date_to_bounds(date)

        return self.db.get_period_readings(bounds[0], bounds[1])

    @list_to_df
    def getReadingsInDatePeriod(self, start_date, end_date) -> List:
        """_summary_

        Args:
            start_date (_type_): _description_
            end_date (_type_): _description_

        Returns:
            List: _description_
        """
        start = date_to_bounds(start_date)[0]
        end = date_to_bounds(end_date)[0]
        return self.db.get_period_readings(start, end)
    
      
    def getRealtimeKWh(self, past_hours:int):
        """_summary_

        Args:
            df (_type_): _description_
            past_hours (int): _description_

        Returns:
            _type_: _description_
        """
        df = self.getReadingsInPastHrs(past_hours)
        print(df.columns)
        return df.query("reading_time>=@stop")['watt_hours'].sum()/1000




def date_to_bounds(date):
    """Returns timestamps corresponding to `date` midnight and end of day
        (midnight, end of day)
    Args:
        date (_type_): Date to get bounds.
    """
    midnight = dt.combine(date, dt.min.time()).timestamp() * 1000
    end_of_day = dt.combine(date, dt.max.time()).timestamp() * 1000

    return (midnight, end_of_day)

past_hrs_millis = lambda x: round(time.time() * 1000) - (x*3_600_000)
