from typing import Any


def success_response(message: str = "", data: Any = None) -> dict[str, Any]:
    return {"success": True, "error": None, "message": message, "data": data}


def error_response(message: str, error: str | None = None, data: Any = None) -> dict[str, Any]:
    return {"success": False, "error": error, "message": message, "data": data}
