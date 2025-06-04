from queue import Queue

class Trie:
    """ String trie """
    def __init__(self):
        self.key = ''
        self.value = None
        self.children = {} # 将 children 从列表改为字典，以支持任意字符
        self.isEnd = False

    def insert(self, key: str, value):
        search_key = key.lower() 

        node = self
        for c in search_key: # 不再需要 ord(c) - 97 的逻辑，直接使用字符作为字典键
            if c not in node.children:
                node.children[c] = Trie()
            node = node.children[c]

        node.isEnd = True
        node.key = key # 存储原始大小写的 key
        node.value = value

    def get(self, key, default=None):
        search_key = key.lower()
        node = self.searchPrefix(search_key)
        if not (node and node.isEnd):
            return default

        return node.value

    def searchPrefix(self, prefix):
        prefix = prefix.lower() # 搜索前缀也转为小写
        node = self
        for c in prefix:
            if c not in node.children:
                return None
            node = node.children[c]

        return node

    def items(self, prefix):
        node = self.searchPrefix(prefix)
        if not node:
            return []

        q = Queue()
        result = []
        q.put(node)

        while not q.empty():
            node = q.get()
            if node.isEnd:
                result.append((node.key, node.value)) # 返回原始大小写的 key

            for child_node in node.children.values(): # 遍历字典的 values
                if child_node: # 确保子节点存在
                    q.put(child_node)

        return result
