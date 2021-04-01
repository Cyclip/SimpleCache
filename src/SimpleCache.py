import hashlib  # Hash filenames
from pathlib import Path  # Cache dir
from functools import wraps  # Decorators
import zlib  # Compression for file sizes
import pickle  # Store objects
import shutil  # Clear cache faster
import logging
import os


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

        maxItemSize (int/None)              :   Maximum items in cache. Set to None if you want to use only maxSize
                                                Default: None
                                                This attribute cannot be accessed, but can be changed through set_maxItemSize()


        evictionSize (int)                  :   Number of LRU items to evict when cache is full
                                                Default: 1
                                                This attribute can be accessed and changed.

        startEmpty (bool)                   :   Start with an empty cache.
                                                WILL ERASE ALL PREVIOUS CACHE obviously
                                                Default: False

        compress (bool)                     :   Use compression when writing/reading cache. It reduces space used, but may
                                                be disabled if optimisation is lacking.
                                                Default: True

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
        maxItemSize=None,
        evictionSize=1,
        startEmpty=False,
        compress=True,
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

            maxItemSize (int/None)              :   Maximum items in cache. Set to None if you want to use only maxSize
                                                    Default: None
                                                    This attribute cannot be accessed, but can be changed through set_maxItemSize()


            evictionSize (int)                  :   Number of LRU items to evict when cache is full
                                                    Default: 1
                                                    This attribute can be accessed and changed.

            startEmpty (bool)                   :   Start with an empty cache.
                                                    WILL ERASE ALL PREVIOUS CACHE obviously
                                                    Default: False

            compress (bool)                     :   Use compression when writing/reading cache. It reduces space used, but may
                                                    be disabled if optimisation is lacking.
                                                    Default: True

        Attributes:                                 (Including parameters if stated)
            __recentAccessed (list)                 Lists the recently accessed nodes in order of when it was accessed.
                                                    This is so least recently used nodes can be evicted to gain space.

            hits (int)                              All successful cache queries (when a value is found in cache)

            misses (int)                            All unsuccessful cache queries (when a value is not found in cache)

        """
        self.cacheDir = cacheDir
        self.algorithm = algorithm
        self.__maxSize = maxSize
        self.__maxItemSize = maxItemSize
        self.evictionSize = evictionSize
        self.__compress = compress

        self.__recentAccessed = []
        self.hits = 0
        self.misses = 0
        self.__logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        Path(self.cacheDir).mkdir(exist_ok=True)

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
        shutil.rmtree(self.cacheDir)  # Remoeve the cache directory
        os.mkdir(self.cacheDir)  # Create cache dir again
        self.__recentAccessed = []  # Reset recent accessed nodes

    def set_maxSize(self, maxSize):
        """
        Set the max cache size in bytes and adapt to the
        new changes.

        Parameters:
            maxSize (int/None)      Set the new maxSize value
        """
        self.__logger.info(f"Setting max size to {maxSize}")
        self.__maxSize = maxSize  # Set max size
        self.__handle_cache_size()  # Adapt to new changes

    def set_maxItemSize(self, maxItemSize):
        """
        Set the max cache item size and adapt to the new
        changes.

        Parameters:
            maxItemSize (int/None)  Maximum item size
        """
        self.__logger.info(f"Setting max item size to {maxItemSize}")
        self.__maxItemSize = maxItemSize
        self.__handle_cache_size()

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
        hits, misses, cacheSizeBytes, cacheSize = (
            self.hits,
            self.misses,
            self.__get_cache_size(),
            len(self.__recentAccessed),
        )
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

        # Hash with the specified algorithm and hexdigest
        # to produce a string
        fname = self.algorithm(
            "".join([func.__name__.encode("utf8"), pickle.dumps(args)])
        ).hexdigest()

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
            content = self.__handle_decompression(f.read())
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
            final = self.__handle_compression(packed)
            f.write(final)

        node = os.path.relpath(fileName, "cache")
        self.__recentAccessed.insert(0, node)

    def __handle_compression(self, x):
        """
        Compress if compression is enabled, else return the value as-is

        Paramters:
            x (bytes)                               Text to compress

        Returns:
            x (bytes)                               Text compressed/retained
        """
        if self.__compress:
            return zlib.compress(x)
        return x

    def __handle_decompression(self, x):
        """
        Deompress if compression is enabled, else return the value as-is

        Paramters:
            x (bytes)                               Text to decompress

        Returns:
            x (bytes)                               Text decompressed/retained
        """
        if self.__compress:
            return zlib.decompress(x)
        return x

    def __handle_cache_size(self):
        """
        Decide whether or not the cache size has been exceed and if so,
        make enough room for more cache to be stored. As it is based off of
        bytes, cache may exceed the limit after writing to cache following
        this.

        To counter, evictionSize can be used to reduce the possibility of
        this happening. maxItemSize can also place a hard limit on the amount
        of cached items.
        """
        if self.__maxSize is not None:
            self.__handle_cache_size_bytes()
        if self.__maxItemSize is not None:
            self.__handle_cache_size_items()

    def __handle_cache_size_bytes(self):
        cacheSize = self.__get_cache_size()
        if cacheSize > self.__maxSize:
            # Cache is full
            self.__logger.info(
                f"Cache size exceeds max size ({cacheSize} > {self.__maxSize})"
            )
            self.__evict(self.evictionSize)

    def __handle_cache_size_items(self):
        cacheSize = len(self.__recentAccessed)
        if cacheSize > self.__maxItemSize:
            # Cache is full
            self.__logger.info(
                f"Cache item size exceeds max item size ({cacheSize} > {self.__maxItemSize})"
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
