from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from utils import LLM
from models.user import User


class UserQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    intents: List[str] = Field(
        description="List of detected intents: 'category', 'source', 'nearby', 'search', 'score', 'time_frame'"
    )
    entities: List[str] = Field(
        description="Raw extracted entities like people, organizations, or locations"
    )
    user: Optional[User] = Field(None)

    # Normalized parameters parsed directly from the query
    category: Optional[str] = Field(
        None,
        description="Normalized category if intent includes 'category'. Must match: 'Technology', 'Business', 'Sports', 'General', etc.",
    )
    source: Optional[str] = Field(
        None, description="Normalized source name"
    )
    location_name: Optional[str] = Field(
        None, description="Location name string'"
    )
    search_query: Optional[str] = Field(
        None, description="Search keywords"
    )
    published_after: Optional[str] = Field(
        None, description="Time filter. ISO 8601 format"
    )
    published_before: Optional[str] = Field(
        None, description="Time filter. ISO 8601 format"
    )
    score_threshold: Optional[float] = Field(
        None, description="Threshold for relevance score"
    )
    radius: Optional[float] = Field(
        None, description="Radius in km"
    )

    @classmethod
    def from_query(cls, query: str, llm: LLM) -> "UserQuery":
        import json

        analysis_prompt = f"""
        You are an expert in analyzing user queries for a news application.
        Your task is to analyze the following user query and extract structured information.
        
        Query: "{query}"
        
        Return the result as a JSON object with the following fields:
        - intents: List of detected intents. Possible values: 'category', 'source', 'nearby', 'search', 'score', 'time_frame'
        - entities: List of extracted entities like people, organizations, or locations
        - category: Normalized category if intent includes 'category'. Must match: 'Technology', 'Business', 'Sports', 'General', etc.
        - source: Normalized source name if intent includes 'source'
        - location_name: Location name string if intent includes 'nearby'
        - search_query: Extracted keywords for text search. CRITICAL: If the user is just asking for a predefined category (e.g., "Entertainment"), DO NOT include it here. Only use search_query for specific keywords, names, or events not covered by the category.
        - published_after: Extracted time filter. Must be normalized to ISO 8601 format
        - published_before: Extracted time filter. Must be normalized to ISO 8601 format
        """

        response = llm.generate_content("gemini-2.5-flash", analysis_prompt)

        # clean markdown fences
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]

        response_data = json.loads(cleaned_response.strip())

        # handle case where LLM returns list instead of string
        if isinstance(response_data.get("search_query"), list):
            sq_list = response_data["search_query"]
            response_data["search_query"] = " ".join(sq_list) if sq_list else None

        return cls(**response_data)
