from models import UserQuery
from repositories.dbquery_builder import DBQueryBuilder

query = UserQuery(intents=["search"], entities=[], search_query="latest news on AI")
builder = DBQueryBuilder()
q, p = builder.build_query(query, limit=2)
print("Query:", q)
print("Params:", p)
