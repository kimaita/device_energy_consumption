from typing import List, Dict

def get_devices(client, thing_group) -> List[str]:
    """Gets a list of sensors registered under a ThingGroup

    Returns:
        List[str]: List of sensors
    """
    devices = []
    next_token = ''

    while True:
        res = response(client, thing_group, next_token)
        devices += res['things']
        if 'nextToken' in res:
            next_token = res['nextToken']
        else:
            break

    return devices


def response(client, thing_group:str, next_token: str) -> Dict:
    """Executes the actual call to aws IoT

    Args:
        next_token (str): string to retrieve the next set of results

    Returns:
        Dict: a dictionary with a list of thing names, the next_token
    """
    return client.list_things_in_thing_group(
        thingGroupName=thing_group,
        recursive=False,
        nextToken=next_token,
        maxResults=100
    )
