from pymilvus import connections, utility, Collection, FieldSchema, DataType, CollectionSchema

def connect():
    connections.connect("default", host="127.0.0.1", port=19530)

def get_existing_collection(collection_name):
    connect()
    collection = Collection(collection_name)
    collection.load()
    return collection

def init_collection(collection_name):
    connect()
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="metadata_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2500),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields=fields, description=collection_name)
    collection = Collection(name=collection_name, schema=schema)
    index_params={
        "metric_type":"COSINE",
        "index_type":"IVF_FLAT",
        "params":{"nlist":128}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection

def get_collections():
    connect()
    return utility.list_collections()