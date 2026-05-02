try:
    from aiohttp import web
    from server import PromptServer
except ImportError:
    PromptServer = None
    web = None

from .config import load_config


if PromptServer is not None and web is not None:
    routes = PromptServer.instance.routes

    # Returns the current Mememizator config as JSON.
    @routes.get("/artemko7v/mememizator/config")
    async def mememizator_config_route(request):
        return web.json_response(load_config())
