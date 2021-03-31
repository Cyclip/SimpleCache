import hashlib  # Hash filenames
import pathlib  # Cache dir
import os
from functools import wraps  # Decorators
import zlib  # Compression for file sizes
import pickle  # Store objects
import shutil  # Clear cache faster
import logging


class Cache:
    """
    Class to implement a simple pure-python caching system with files, without
    using up too much memory.

    Parameters:
        cacheDir (str)                      :   Specify where the cache will be stored.
                                                Default: "cache"
                                                This attribute can be accessed, but should not be changed.

        algorithm (function)                :   Hashing algorithm from hashlib
                                                Default: hashlib.sha1
                                                This attribute can be accessed, but should not be changed.

        maxSize (int)                       :   Maximum cache size in bytes
                                                Default: 5000000
                                                This attribute cannot be accessed, but can be changed through set_maxSize()

        evictionSize (int)                  :   Number of LRU items to evict when cache is full
                                                Default: 1
                                                This attribute can be accessed and changed.

        startEmpty (bool)                   :   Start with an empty cache.
                                                WILL ERASE ALL PREVIOUS CACHE obviously
                                                Default: False

    Attributes:                                 (Including parameters if stated)
        __recentAccessed (list)                 Lists the recently accessed nodes in order of when it was accessed.
                                                This is so least recently used nodes can be evicted to gain space.

        hits (int)                              All successful cache queries (when a value is found in cache)

        misses (int)                            All unsuccessful cache queries (when a value is not found in cache)

    Functions:
        clear()                             :   Clear cache

        set_maxSize(
            maxSize (int)                   :   Set maximum cache size
        )

        get_info()                          :   Get cache info

    Decorators:
        @cache_function
            Cache results of function based on arguments
    """

    def __init__(
        self,
        cacheDir="cache",
        algorithm=hashlib.sha1,
        maxSize=1000000,
        evictionSize=1,
        startEmpty=False,
    ):
        """
        Constructs system with necessary attributes.

        Parameters:
            cacheDir (str)                      :   Specify where the cache will be stored.
                                                    Default: "cache"
                                                    This attribute can be accessed, but should not be changed.

            algorithm (function)                :   Hashing algorithm from hashlib
                                                    Default: hashlib.sha1
                                                    This attribute can be accessed, but should not be changed.

            maxSize (int)                       :   Maximum cache size in bytes
                                                    Default: 5000000
                                                    This attribute cannot be accessed, but can be changed through set_maxSize()

            evictionSize (int)                  :   Number of LRU items to evict when cache is full
                                                    Default: 1
                                                    This attribute can be accessed and changed.

            startEmpty (bool)                   :   Start with an empty cache.
                                                    WILL ERASE ALL PREVIOUS CACHE obviously
                                                    Default: False

        Attributes:                                 (Including parameters if stated)
            __recentAccessed (list)                 Lists the recently accessed nodes in order of when it was accessed.
                                                    This is so least recently used nodes can be evicted to gain space.

            hits (int)                              All successful cache queries (when a value is found in cache)

            misses (int)                            All unsuccessful cache queries (when a value is not found in cache)

        """
        self.cacheDir = cacheDir
        self.algorithm = algorithm
        self.__maxSize = maxSize
        self.evictionSize = evictionSize

        self.__recentAccessed = []
        self.hits = 0
        self.misses = 0
        self.__logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        pathlib.Path(self.cacheDir).mkdir(exist_ok=True)

        if startEmpty:
            self.clear()

    def cache_function(self, func):
        """
        Implements the cache system onto a function.

        No parameters, nor arguments as all settings are set during construction.
        """

        @wraps(func)
        def wrapper(*args):
            self.__logger.info(f"Called {func.__name__} with {args}")
            fileName = self.__build_file_name(func, args)

            if os.path.isfile(fileName):
                # Result is already stored in cache
                # Retrieve return value from cache
                return self.__read_cache(fileName)
            else:
                # Result is not stored in cache
                # Run function
                if len(args) > 0:
                    returnVal = func(args)
                else:
                    returnVal = func()

                # Store value in cache
                self.__write_cache(fileName, returnVal)

                # Give return value
                return returnVal

        return wrapper

    def clear(self):
        """
        Clear cache for this Cache() instance.
        If 2 instances share the same directory, it will
        affect both instances.
        """
        self.__logger.info("Cleared cache")
        shutil.rmtree(self.cacheDir)
        os.mkdir(self.cacheDir)

    def set_maxSize(self, maxSize):
        """
        Set the max cache size in bytes and adapt to the
        new changes.

        Parameters:
            maxSize (int)                           Set the new maxSize value
        """
        self.__logger.info("Cleared cache")
        self.__maxSize = maxSize  # Set max size
        self.__handle_cache_size()  # Adapt to new changes

    def get_info(self):
        """
        Get cache system information

        Returns:
            {
                "hits": hits,                       (int) Successful cache queries
                "misses": misses,                   (int) Unsuccessful cache queries
                "cacheSize": {
                    "bytes": cacheSizeBytes,        (int) Cache size used up in bytes
                    "items": cacheSize              (int) Items in cache
                },
                "filled": filled,                   (float) Percentage of cache used up (0.0-1.0)
            }
        """
        hits = self.hits
        misses = self.misses
        cacheSizeBytes = self.__get_cache_size()
        cacheSize = len(self.__recentAccessed)
        filled = cacheSizeBytes / self.__maxSize

        return {
            "hits": hits,
            "misses": misses,
            "cacheSize": {"bytes": cacheSizeBytes, "items": cacheSize},
            "filled": filled,
        }

    def __build_file_name(self, func, args):
        """
        Using the function name and arguments, build an appropriate file
        file to store in

        Parameters:
            func (function)                         The function which was specifically called
            args (tuple)                            Args for the function which was specifically called

        Returns:
            pathToFile (str)                        A path to the cache file (i.e
                                                    'cache\\0ac817ca5029584c7e4dbc34ca564d97306a4170')
        """
        # Build a unique string to hash
        self.__logger.info(f"Building file name for {func.__name__} with {args}")
        fname = func.__name__

        # Hash with the specified algorithm and hexdigest
        # to produce a string
        fname = self.algorithm(fname.encode("utf8") + pickle.dumps(args)).hexdigest()

        pathToFile = os.path.join(self.cacheDir, fname)
        self.__logger.info(f"Built path {pathToFile}")
        return pathToFile

    def __read_cache(self, fileName):
        """
        Retrieve a file contents, decompress and extract python objects and
        return them.

        Arguments:
            fileName (str)                          Path to the cache file which is being read

        Returns:
            variables (mixed)                       Variable name is literally 'variables'. Returns python
                                                    objects of an unknown type.
        """
        self.__logger.info(f"Cache hit - {fileName}")
        # Cache hit
        with open(fileName, "rb") as f:
            content = zlib.decompress(f.read())
            variables = pickle.loads(content)

        # Move node to front
        node = os.path.relpath(fileName, "cache")
        self.__shift_node(node)

        return variables

    def __write_cache(self, fileName, returnVal):
        """
        Dump python objects into an encoded string, compress and write to
        cache.

        Parameters:
            fileName (str)                          Path to the cache file which will be written in

            returnVal (mixed)                       The function's return value to write into cache
        """
        # Cache miss
        self.__logger.info(f"Cache miss: {fileName}")
        self.__handle_cache_size()

        with open(fileName, "wb") as f:
            packed = pickle.dumps(returnVal)
            compressed = zlib.compress(packed)
            f.write(compressed)

        node = os.path.relpath(fileName, "cache")
        self.__recentAccessed.insert(0, node)

    def __handle_cache_size(self):
        """
        Decide whether or not the cache size has been exceed and if so,
        make enough room for more cache to be stored. As it is based off of
        bytes, cache may exceed the limit after writing to cache following
        this.

        To counter, evictionSize can be used to reduce the possibility of
        this happening.
        """
        cacheSize = self.__get_cache_size()
        if cacheSize > self.__maxSize:
            # Cache is full
            self.__logger.info(
                f"Cache size exceeds max size ({cacheSize} > {self.__maxSize})"
            )
            self.__evict(self.evictionSize)

    def __shift_node(self, node):
        """
        Shift the recently used node to the top of the list - based off of
        the LRU caching concept.

        Paramters:
            node (int)                              Index of node to move to the top
        """
        index = self.__recentAccessed.index(node)

        self.__logger.info(f"Shifting node {node}: {index}")

        self.__recentAccessed = [
            self.__recentAccessed.pop(index)
        ] + self.__recentAccessed

    def __get_cache_size(self):
        """
        Quickly retrieve existing cache size used.

        Returns:
            total (int)                             The total cache size in bytes
        """
        total = 0
        for entry in os.scandir(self.cacheDir):
            total += entry.stat(follow_symlinks=False).st_size
        self.__logger.info(f"Cache size: {total} bytes")
        return total
