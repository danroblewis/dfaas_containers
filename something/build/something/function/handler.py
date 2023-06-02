import time
import sys


def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """

    time.sleep(1)
    return '> ' + str(req)


if __name__ == "__main__":
    print(handle(sys.stdin.read()))
