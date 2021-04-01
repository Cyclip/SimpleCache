# SimpleCache

Pure-python implementation of Least Recently Used (LRU) caching. It allows a developer to easily use memoization on expensive function calls.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites
No other modules are required
- Python >=3.7.9
- SimpleCache module

#### Installing the module
`python -m pip install cyclip-simplecache`

### Examples
**Minimal usage**
```Python
from SimpleCache import Cache

cache = Cache()

@cache.cache_function
def expensive_function(n, m):
    total = 0
    for i in n:
        for j in m:
            total += i * j
    return total
```

**All arguments**
```Python
from SimpleCache import Cache
from hashlib import sha256

cache = Cache(
    cacheDir="caches/cache",    # Where cache will be stored
    algorithm=sha256,           # Algorithm used
    maxSize=5000000,            # Max cache storage
    maxItemSize=250000,         # Max items cached
    evictionSize=20,            # Items evicted
    compress=False              # Compress cache to save storage
)

@cache.cache_function
def expensive_function(n):
    total = 0
    for i in n:
        for j in m:
            total += i * j
    return total
```

## Built With

* [Python](https://www.python.org/) - Programming language

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).

## Author

**Cyclip** - [GitHub](https://github.com/Cyclip)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Project status
Project is complete, and the code is not guaranteed to be updated.
