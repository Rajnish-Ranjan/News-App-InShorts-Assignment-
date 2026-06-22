from models.user import User
from models.user_query import UserQuery
from repositories.dbquery_builder import DBQueryBuilder

user = User(lat=40.7128, lon=-74.0060)
query = UserQuery(intents=["nearby"], entities=[], radius=50, user=user)
builder = DBQueryBuilder()
q, p = builder.build_query(query, limit=2)
print("Query:", q)
print("Params:", p)
