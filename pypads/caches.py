import sys
from logging import debug

import mlflow

from pypads.util import dict_merge


def cache_merge(*dicts):
    merged = {}
    for d in dicts:
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, dict):
                    node = merged.setdefault(key, {})
                    merged[key] = dict_merge(node, value)
                elif isinstance(value, list):
                    node = merged.setdefault(key, [])
                    merged[key] = node.extend(value)
                elif isinstance(value, set):
                    s: set = merged.setdefault(key, set())
                    for v in value:
                        if v in s:
                            merged = dict_merge(v, s.pop(v))
                            s.add(merged)
                        else:
                            s.add(v)
                elif isinstance(value, Cache):
                    node = merged.setdefault(key, Cache())
                    merged[key] = value.merge(node)
                else:
                    merged[key] = value
    return merged


class Cache:
    def __init__(self):
        self._cache = {}

    @property
    def cache(self):
        return self._cache

    def merge(self, other):
        self._cache = cache_merge(self.cache, other.cache)
        return self

    def add(self, key, value):
        if key in self.cache:
            if isinstance(value, dict):
                self.cache.get(key).update(value)
            else:
                self.cache[key] = value
        else:
            self.cache.update({key: value})

    def pop(self, key, default=None):
        if key in self.cache:
            return self.cache.pop(key, default)
        return None

    def get(self, item, default=None):
        return self._cache.get(item,default)

    def items(self):
        return self._cache.items()

    def exists(self, key):
        return key in self._cache

    def clear(self):
        self._cache = {}

    # def __getstate__(self):
    #     """
    #     Overwrite standard pickling by excluding the functions
    #     :return:
    #     """
    #     # TODO can't pickle functions
    #     state = self.__dict__.copy()
    #     if "cache_cleanup" in self._cache:
    #         del state["_cache"]
    #     return state
    #
    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     if hasattr(self, "_cache") or self._cache is None:
    #         self._cache = {}


class PypadsRunCache(Cache):
    def __init__(self, run):
        super().__init__()
        self._run = run or mlflow.active_run()
        if not self._run:
            raise ValueError("No active run for run cache found.")

    @property
    def run(self):
        return self._run

    def run_id(self):
        return self._run.info.run_id

    def register_cleanup_fn(self):
        from pypads.base import get_current_pads
        pads = get_current_pads()

        def cleanup_cache(run_id=self.run_id()):
            from pypads.base import get_current_pads
            pads = get_current_pads()
            pads.cache.run_delete(run_id)
            debug("Cleared run cache after run " + run_id)

        pads.api.register_post_fn("cache_cleanup", cleanup_cache, order=sys.maxsize)


class PypadsCache(Cache):

    def __init__(self):
        super().__init__()
        self._run_caches = {}

    def merge(self, other):
        super().merge(other)
        self._run_caches = cache_merge(self.run_caches, other.run_caches)

    @property
    def run_caches(self):
        return self._run_caches

    def run_cache(self, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches.get(run)

    def _get_run(self, run_id=None):
        if run_id is None:
            run = mlflow.active_run()
        else:
            run = mlflow.get_run(run_id)
        return run

    def run_init(self, run_id=None):
        run = self._get_run(run_id)
        if not run:
            raise ValueError("No run is active. Couldn't init run cache.")
        if run.info.run_id not in self._run_caches:
            run_cache = PypadsRunCache(run)
            self._run_caches[run.info.run_id] = run_cache
            run_cache.register_cleanup_fn()
        return run

    def run_add(self, key, value, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run.info.run_id].add(key, value)

    def run_pop(self, key, run_id=None, default=None):
        run = self.run_init(run_id)
        return self._run_caches[run.info.run_id].pop(key, default=default)

    def run_remove(self, key, run_id=None):
        run = self.run_init(run_id)
        del self._run_caches[run.info.run_id][key]

    def run_get(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run.info.run_id].get(key)

    def run_exists(self, key, run_id=None):
        run = self.run_init(run_id)
        return self._run_caches[run.info.run_id].exists(key)

    def run_clear(self, run_id=None):
        run = self.run_init(run_id)
        self._run_caches[run.info.run_id].clear()

    def run_delete(self, run_id=None):
        run = self.run_init(run_id)
        del self._run_caches[run.info.run_id]