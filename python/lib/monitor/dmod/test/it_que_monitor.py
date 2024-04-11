import unittest


# TODO: rework testing here with two mock subtypes (separate for Docker and Redis testing)

class IntegrationTestRedisManager(unittest.TestCase):
    """
        Tests of the redis implementation of the abstract ResourceManager Interface
        Tests some additional functions not in the interface but found in the RedisManager
    """
    def dict_values_to_string(self, dict):
        """
            Helper function that converts all dict values to string
            Useful when comparing to returns of raw redis queries, since
            everything in redis is a string
        """
        for k, v in dict.items(): #todo could be nice and recurse for nested dicts
            dict[k] = str(v)
        return dict

    def clear_redis(self):
        """
            Helper function to clear the redis instance of all keys
            Returns
            -------
            count The number of removed keys
        """
        count = 0
        for k in self.redis.scan_iter("*"):
          self.redis.delete(k)
          count += 1
        return count

    def setUp(self) -> None:

        pass

    def tearDown(self) -> None:
        pass
