"""可选集合首次写入时创建索引，避免启动就产生一批空集合。"""

from threading import Lock


class DeferredIndexes:
    """每个存储实例最多初始化一次；索引未成功创建时不放行写入。"""

    def __init__(self, collection, *models):
        self.collection = collection
        self.models = models
        self._ready = False
        self._lock = Lock()

    def ensure(self):
        """同步驱动调用由使用方放入工作线程；同进程并发初始化串行。"""
        with self._lock:
            if not self._ready:
                if self.models:
                    existing = self.collection.index_information()
                    # 逐个保留全部选项；部分测试驱动的 create_indexes 会漏掉
                    # partialFilterExpression，误把历史完成记录也纳入唯一限制。
                    for model in self.models:
                        spec = dict(model.document)
                        keys = list(spec.pop("key").items())
                        current = existing.get(spec["name"])
                        if current is not None:
                            expected = {
                                "key": keys,
                                **{k: v for k, v in spec.items() if k != "name"},
                            }
                            if any(
                                current.get(key) != value
                                for key, value in expected.items()
                            ):
                                raise RuntimeError(
                                    "数据库同名索引配置不匹配，请先检查索引"
                                )
                            continue
                        self.collection.create_index(keys, **spec)
                self._ready = True
