import json
from enum import Enum
from abc import ABC, abstractmethod

from models import UserQuery, Location, User
from utils import preprocess_search_text


class SQLClauseType(Enum):
    SELECT = 0
    WHERE = 1
    ORDER_BY = 2
    LIMIT = 3
    OFFSET = 4


class SQLClause:
    def __init__(self, type: SQLClauseType, value=None, parameter=None):
        self.type = type
        self.value = value
        self.parameter = parameter

    def __eq__(self, other):
        if not isinstance(other, SQLClause):
            return False
        return self.type == other.type and self.value == other.value

    def __hash__(self):
        return hash((self.type, self.value))


class IntentStrategy(ABC):
    @abstractmethod
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        pass

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        return []


class CategoryStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        return [
            SQLClause(
                type=SQLClauseType.SELECT, value="publication_date as sort_value"
            ),
            SQLClause(
                type=SQLClauseType.WHERE,
                value="category @> %s::jsonb",
                parameter=json.dumps([user_query.category.lower()]),
            ),
            SQLClause(
                type=SQLClauseType.ORDER_BY, value="publication_date DESC, id DESC"
            ),
        ]

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(publication_date, id) < (%s, %s)",
                parameter=[cursor_data["v"], cursor_data["id"]],
            )
        ]


class SearchStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        if user_query.search_query and user_query.search_query.strip():
            # Preprocess to remove common stop words and unwanted characters
            cleaned_query = preprocess_search_text(user_query.search_query)
            if not cleaned_query:
                return []

            # Convert "Viral Social Media Posts" to "Viral OR Social OR Media OR Posts"
            words = cleaned_query.split()
            sq = " OR ".join(words)
            return [
                SQLClause(
                    type=SQLClauseType.SELECT,
                    value="((ts_rank(search_vector, websearch_to_tsquery('english', %s)) * 10.0) + relevance_score) as sort_value",
                    parameter=sq,
                ),
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="search_vector @@ websearch_to_tsquery('english', %s)",
                    parameter=sq,
                ),
                SQLClause(
                    type=SQLClauseType.ORDER_BY,
                    value="((ts_rank(search_vector, websearch_to_tsquery('english', %s)) * 10.0) + relevance_score) DESC, id DESC",
                    parameter=sq,
                ),
            ]
        return []

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        cleaned_query = preprocess_search_text(user_query.search_query)
        if not cleaned_query:
            return []
        sq = " OR ".join(cleaned_query.split())
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(((ts_rank(search_vector, websearch_to_tsquery('english', %s)) * 10.0) + relevance_score), id) < (%s, %s)",
                parameter=[sq, cursor_data["v"], cursor_data["id"]],
            )
        ]


class NearbyStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        clauses = []

        if user_query.user and user_query.user.lat and user_query.user.lon:
            clauses.insert(
                0,
                SQLClause(
                    type=SQLClauseType.SELECT,
                    value="ST_Distance(geolocation, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as sort_value",
                    parameter=[user_query.user.lon, user_query.user.lat],
                ),
            )
            distance_clause = SQLClause(
                type=SQLClauseType.ORDER_BY,
                value="ST_Distance(geolocation, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) ASC, id ASC",
                parameter=[user_query.user.lon, user_query.user.lat],
            )
            clauses.insert(1, distance_clause)

            if user_query.radius is not None:
                radius_meters = user_query.radius * 1000
                clauses.append(
                    SQLClause(
                        type=SQLClauseType.WHERE,
                        value="ST_DWithin(geolocation, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)",
                        parameter=[user_query.user.lon, user_query.user.lat, radius_meters],
                    )
                )

        if user_query.location_name is None:
            return clauses

        location_details = Location.from_name(user_query.location_name)

        if location_details is None:
            return clauses

        if location_details.bounding_box:
            bounding_box = location_details.bounding_box
            clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="geolocation && ST_MakeEnvelope(%s, %s, %s, %s, 4326)::geography",
                    parameter=[
                        float(bounding_box[2]),
                        float(bounding_box[0]),
                        float(bounding_box[3]),
                        float(bounding_box[1]),
                    ],
                )
            )
        elif location_details.radius:
            lat = location_details.lat
            lon = location_details.lon
            dynamic_radius = location_details.radius
            clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="""ST_DWithin(
                            geolocation,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                            %s
                        )""",
                    parameter=[lon, lat, dynamic_radius],
                )
            )

        return clauses

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        if not (user_query.user and user_query.user.lat and user_query.user.lon):
            return []
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(ST_Distance(geolocation, ST_SetSRID(ST_MakePoint(%s, %s), 4326)), id) > (%s, %s)",
                parameter=[
                    user_query.user.lon,
                    user_query.user.lat,
                    cursor_data["v"],
                    cursor_data["id"],
                ],
            )
        ]


class TimeFrameStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        clauses = [
            SQLClause(
                type=SQLClauseType.SELECT,
                value="publication_date as sort_value",
                parameter=None,
            ),
            SQLClause(
                type=SQLClauseType.ORDER_BY,
                value="publication_date DESC, id DESC",
                parameter=None,
            ),
        ]
        if user_query.published_after and user_query.published_before:
            clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="publication_date BETWEEN %s AND %s",
                    parameter=[
                        user_query.published_after,
                        user_query.published_before,
                    ],
                )
            )
        return clauses

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(publication_date, id) < (%s, %s)",
                parameter=[cursor_data["v"], cursor_data["id"]],
            )
        ]


class SourceStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        clauses = [
            SQLClause(
                type=SQLClauseType.SELECT, value="publication_date as sort_value"
            ),
            SQLClause(
                type=SQLClauseType.ORDER_BY,
                value="publication_date DESC, id DESC",
                parameter=None,
            ),
        ]
        if user_query.source:
            clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="source_name = %s",
                    parameter=user_query.source,
                )
            )
        return clauses

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(publication_date, id) < (%s, %s)",
                parameter=[cursor_data["v"], cursor_data["id"]],
            )
        ]


class RelevanceStrategy(IntentStrategy):
    def apply(self, user_query: UserQuery) -> list[SQLClause]:
        clauses = [
            SQLClause(
                type=SQLClauseType.SELECT,
                value="relevance_score as sort_value",
                parameter=None,
            ),
            SQLClause(
                type=SQLClauseType.ORDER_BY,
                value="relevance_score DESC, id DESC",
                parameter=None,
            ),
        ]
        if user_query.score_threshold is not None:
            clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="relevance_score >= %s",
                    parameter=user_query.score_threshold,
                )
            )
        return clauses

    def get_cursor_clause(
        self, cursor_data: dict, user_query: UserQuery
    ) -> list[SQLClause]:
        return [
            SQLClause(
                type=SQLClauseType.WHERE,
                value="(relevance_score, id) < (%s, %s)",
                parameter=[cursor_data["v"], cursor_data["id"]],
            )
        ]


class DBQueryBuilder:

    def __init__(self):
        self.strategies = {
            "nearby": NearbyStrategy(),
            "time_frame": TimeFrameStrategy(),
            "category": CategoryStrategy(),
            "search": SearchStrategy(),
            "source": SourceStrategy(),
            "score": RelevanceStrategy(),
        }

    def get_query_clauses(
        self, user_query: UserQuery, cursor_data: dict = None
    ) -> list[SQLClause]:

        print("User Query:", user_query)
        # Sort intents to exactly match the priority order defined in the strategies dictionary
        strategy_order = list(self.strategies.keys())
        user_query.intents.sort(
            key=lambda intent: (
                strategy_order.index(intent) if intent in strategy_order else 999
            )
        )

        all_clauses = []
        primary_strategy_applied = False
        for query_intent in user_query.intents:
            strategy = self.strategies.get(query_intent)
            if not strategy:
                continue

            try:
                clauses = strategy.apply(user_query)
                if not clauses:
                    continue

                all_clauses.extend(clauses)
                if cursor_data and not primary_strategy_applied:
                    cursor_clauses = strategy.get_cursor_clause(cursor_data, user_query)
                    if cursor_clauses:
                        all_clauses.extend(cursor_clauses)
                    primary_strategy_applied = True
            except Exception as e:
                print("Error in applying strategy:", e)

        # If no cursor clause applied but we have cursor_data (e.g. no intents)
        if cursor_data and not primary_strategy_applied:
            all_clauses.append(
                SQLClause(
                    type=SQLClauseType.WHERE,
                    value="(relevance_score, id) < (%s, %s)",
                    parameter=[cursor_data["v"], cursor_data["id"]],
                )
            )

        # Add default select and order by if no intents
        if not user_query.intents:
            all_clauses.append(
                SQLClause(
                    type=SQLClauseType.SELECT, value="relevance_score as sort_value"
                )
            )
            all_clauses.append(
                SQLClause(
                    type=SQLClauseType.ORDER_BY, value="relevance_score DESC, id DESC"
                )
            )

        return all_clauses

    def build_query(
        self,
        user_query: UserQuery,
        limit: int = 5,
        cursor_data: dict = None,
    ) -> tuple[str, list]:
        """
        Builds the final SQL query string and parameter list based on strategies.
        """
        clauses = self.get_query_clauses(user_query, cursor_data)

        # Remove duplicates while preserving order
        clauses = list(dict.fromkeys(clauses))

        select_clause = None
        where_conds = []
        where_params = []
        order_by_clause = None

        for clause in clauses:
            if clause.type == SQLClauseType.SELECT:
                if select_clause is None:
                    select_clause = clause
            elif clause.type == SQLClauseType.WHERE:
                where_conds.append(clause.value)
                if clause.parameter is not None:
                    if isinstance(clause.parameter, list):
                        where_params.extend(clause.parameter)
                    else:
                        where_params.append(clause.parameter)
            elif clause.type == SQLClauseType.ORDER_BY:
                if order_by_clause is None:
                    order_by_clause = clause

        query = "SELECT id, title, description, url, publication_date, source_name, category, relevance_score"
        params = []

        if select_clause:
            query += ", " + select_clause.value
            if select_clause.parameter is not None:
                if isinstance(select_clause.parameter, list):
                    params.extend(select_clause.parameter)
                else:
                    params.append(select_clause.parameter)

        query += " FROM news_articles"

        params.extend(where_params)

        if where_conds:
            query += " WHERE " + " AND ".join(where_conds)

        if order_by_clause:
            query += " ORDER BY " + order_by_clause.value
            if order_by_clause.parameter is not None:
                if isinstance(order_by_clause.parameter, list):
                    params.extend(order_by_clause.parameter)
                else:
                    params.append(order_by_clause.parameter)
        else:
            query += " ORDER BY relevance_score DESC, id DESC"

        # Add 1 to limit to check if there is a next page
        query += " LIMIT %s;"
        params.append(limit + 1)

        return query, params
