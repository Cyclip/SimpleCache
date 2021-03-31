import time
import logging

logging.getLogger(__name__)

import SimpleCache

cache = SimpleCache.Cache(maxSize=200000)


@cache.cache_function
def steps_to(stair):
    stair = stair[0]
    if stair == 1:
        return 1
    elif stair == 2:
        return 2
    elif stair == 3:
        return 4
    else:
        return steps_to(stair - 3) + steps_to(stair - 2) + steps_to(stair - 1)


def test(stair):
    start = time.time()
    rv = steps_to(stair)
    end = time.time()

    timeTaken = round(end - start, 6)
    return rv, timeTaken


s = cache.clear()
print(f"[{s}] Cleared cache")
i = 0
while True:
    i += 1
    r, t = test(i)
    print(f"[{i}] {t}s")
    # time.sleep(0.5)
