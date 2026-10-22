"""Mongo 集合存储的公共生命周期；连接统一由应用持有。"""


class MongoCollectionStore:
    """存储只持有集合，阻塞 Mongo 操作由各方法放入工作线程。"""

    def __init__(self, collection):
        self.collection = collection

    async def open(self) -> None:
        """通用存储无初始化写入；可选集合由具体存储首次写入时建立索引。"""

    async def close(self) -> None:
        """集合不单独关闭连接，由应用生命周期释放共享客户端。"""
