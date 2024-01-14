from datetime import datetime

from typing import List
import logging
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class Reading:
    """Encapsulates an Amazon DynamoDB table of our sensor readings."""

    def __init__(self, dyn_resource):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        # The table variable is set during the scenario in the call to
        # 'set_table' if the table exists. Otherwise, it is set by 'create_table'.
        self.table = None

    def log_error(err):
        """_summary_

        Args:
            err (_type_): _description_
        """

    def set_table(self, table_name):
        """
        Determines whether a table exists and stores the table in
        a member variable.

        :param table_name: The name of the table to check.
        :return: True when the table exists; otherwise, False.
        """
        try:
            table = self.dyn_resource.Table(table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                logger.error(
                    "Couldn't check for existence of %s. Here's why: %s: %s",
                    table_name,
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise
        else:
            self.table = table
        return exists

    def get_period_readings(self, start, end) -> List:
        """Scans for readings obtained over a specified period

        Args:
            start: timestamp corresponding to start of period
            end: timestamp corresponding to end pf period 

        Returns:
            List: The list of readings recorded over the given period
        """

        readings = []
        scan_kwargs = {
            "FilterExpression": Key("sample_time").between(int(start), int(end)),
            "ProjectionExpression": "sample_time, device_id, readings.reading_time, readings.power, readings.rms_current, readings.watt_hours",
            "ReturnConsumedCapacity": 'TOTAL',
            "ConsistentRead": True
        }

        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response = self.table.scan(**scan_kwargs)
                readings.extend(response.get("Items", []))
                start_key = response.get("LastEvaluatedKey", None)
                done = start_key is None
        except ClientError as err:
            logger.error(
                "Couldn't get readings for the period %s to %s. Here's why: %s: %s",
                datetime.fromtimestamp(start),
                datetime.fromtimestamp(end),
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            logger.info("The query returned %s items, consuming %s units.",
                        response['Count'],
                        response['ConsumedCapacity']['CapacityUnits'])
            return readings

    def get_latest_readings(self, stop_time) -> List:
        """Scans for readings obtained since a specified time

        Args:
            stop_time: how far back to query

        Returns:
            List: The list of readings recorded since the given time
        """

        readings = []
        scan_kwargs = {
            "FilterExpression": Key("sample_time").gte(int(stop_time)),
            "ProjectionExpression": "sample_time, device_id, readings.reading_time, readings.power, readings.rms_current, readings.watt_hours",
            "ReturnConsumedCapacity": 'TOTAL',
            "ConsistentRead": True
        }

        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response = self.table.scan(**scan_kwargs)
                readings.extend(response.get("Items", []))
                start_key = response.get("LastEvaluatedKey", None)
                done = start_key is None
        except ClientError as err:
            logger.error(
                "Couldn't get readings for the period since %s. Here's why: %s: %s",
                datetime.fromtimestamp(stop_time),
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            logger.info("The query returned %s items, consuming %s units.",
                        response['Count'],
                        response['ConsumedCapacity']['CapacityUnits'])
            return readings
