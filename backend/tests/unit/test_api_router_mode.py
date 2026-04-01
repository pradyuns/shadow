import importlib

from app.config import settings


def _route_paths(api_router) -> set[str]:
    return {route.path for route in api_router.routes}


def test_router_hides_private_routes_in_public_landing_mode(monkeypatch):
    import app.api.v1.router as router_module

    original_mode = settings.public_landing_only_mode
    try:
        monkeypatch.setattr(settings, "public_landing_only_mode", True)
        reloaded = importlib.reload(router_module)
        paths = _route_paths(reloaded.api_router)
        assert "/api/v1/public/beta-signups" in paths
        assert "/api/v1/monitors" not in paths
        assert "/api/v1/auth/login" not in paths
    finally:
        monkeypatch.setattr(settings, "public_landing_only_mode", original_mode)
        importlib.reload(router_module)


def test_router_exposes_full_routes_when_not_in_public_landing_mode(monkeypatch):
    import app.api.v1.router as router_module

    original_mode = settings.public_landing_only_mode
    try:
        monkeypatch.setattr(settings, "public_landing_only_mode", False)
        reloaded = importlib.reload(router_module)
        paths = _route_paths(reloaded.api_router)
        assert "/api/v1/public/beta-signups" in paths
        assert "/api/v1/monitors" in paths
        assert "/api/v1/auth/login" in paths
    finally:
        monkeypatch.setattr(settings, "public_landing_only_mode", original_mode)
        importlib.reload(router_module)
