import json
import base64


def encode_cursor(sort_value, article_id: str) -> str:
    if hasattr(sort_value, "isoformat"):
        sort_value = sort_value.isoformat()

    data = {"v": sort_value, "id": str(article_id)}
    json_str = json.dumps(data)
    return base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> dict | None:
    if not cursor_str:
        return None
    try:
        json_str = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        return json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Invalid cursor: {e}")
