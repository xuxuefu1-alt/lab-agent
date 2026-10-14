import chromadb
from app.config import BASE_DIR
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

# 定义kb chorma 文件路径

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"

_collection = None
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5"
)


def get_collection() -> Collection:
    # 向量库初始化
    global _collection
    if _collection is not None:
        return _collection
    # 创建chroma kb文件夹
    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # 获取chroma client
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # 获取到本地所有向量
    col = client.get_or_create_collection(
        name="lab_agent", embedding_function=_embedding_fn
    )
    if col.count() == 0:
        ids = []  # 序列号
        docs = []  # 文本
        metas = []  # 元数据
        # 获取每个文件
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="UTF-8")  # 文本
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            col.add(ids=ids, documents=docs, metadatas=metas)
    _collection = col
    return col


# 文档检索
def search(query: str):
    col = get_collection()
    count = col.count()
    if count == 0:
        return ""
    res = col.query(query_texts=[query], n_results=min(count, 5))
    docs = (res.get("documents") or [[]])[0]  # [list]
    metas = (res.get("metadatas") or [[]])[0]  # [list]
    distances = (res.get("distances") or [[]])[0]  # [list]
    # 拼接输出格式
    score_parts = []
    for doc, metas, dist in zip(docs, metas, distances):
        score = 1 / (1 + dist)  # 打分
        if score < 0.5:
            continue
        name = metas.get("source")
        score_parts.append({"score": score, "content": f"[{name}\n{doc}]"})
        # 打分排序
    score_parts.sort(key=lambda item: item["score"], reverse=True)
    return "\n\n".join(item["content"] for item in score_parts[:2])
