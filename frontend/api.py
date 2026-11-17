import httpx

from session import UserSession

API_BASE_URL = "http://127.0.0.1:8000/api"


class ApiError(Exception):

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict:
    token = UserSession.get_instance().token
    return {"Authorization": f"Bearer {token}"} if token else {}


def _detaliu(res: httpx.Response) -> str:
    try:
        detail = res.json().get("detail", res.text)
    except ValueError:
        return res.text or f"Eroare HTTP {res.status_code}"
    if isinstance(detail, list):  # erori de validare Pydantic (422)
        return "; ".join(f"{'.'.join(map(str, d.get('loc', [])[1:]))}: {d.get('msg')}" for d in detail)
    return str(detail)


def _request(method: str, path: str, **kwargs):
    try:
        res = httpx.request(method, f"{API_BASE_URL}{path}", headers=_headers(), timeout=10, **kwargs)
    except httpx.ConnectError:
        raise ApiError("Nu s-a putut conecta la serverul backend")
    except httpx.HTTPError as e:
        raise ApiError(f"Eroare de retea: {e}")

    if res.status_code >= 400:
        raise ApiError(_detaliu(res), res.status_code)
    return res.json() if res.content else None


def get(path: str, **kwargs):
    return _request("GET", path, **kwargs)


def post(path: str, **kwargs):
    return _request("POST", path, **kwargs)


def put(path: str, **kwargs):
    return _request("PUT", path, **kwargs)


def delete(path: str, **kwargs):
    return _request("DELETE", path, **kwargs)