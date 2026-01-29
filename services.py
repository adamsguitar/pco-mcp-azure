"""
PCO Services MCP Server with Auth0 authentication.
Based on Auth0's official FastMCP integration pattern.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable

import jwt
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcp.server.auth.routes import create_protected_resource_routes
from pypco import PCO
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", "8080"))

# Initialize PCO client
pco = PCO(
    application_id=os.getenv("PCO_APPLICATION_ID"),
    secret=os.getenv("PCO_SECRET_KEY")
)


class Auth0Middleware(BaseHTTPMiddleware):
    """Middleware to verify Auth0 JWT tokens."""

    def __init__(self, app, domain: str, audience: str):
        super().__init__(app)
        self.domain = domain
        self.audience = audience
        self.jwks_client = None
        self._jwks_uri = f"https://{domain}/.well-known/jwks.json"

    async def _get_signing_key(self, token: str) -> jwt.PyJWK:
        """Fetch the signing key from Auth0's JWKS endpoint."""
        if self.jwks_client is None:
            self.jwks_client = jwt.PyJWKClient(self._jwks_uri)
        return self.jwks_client.get_signing_key_from_jwt(token)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Allow OPTIONS requests for CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing or invalid Authorization header"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self.audience}"'}
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            signing_key = await self._get_signing_key(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )
            # Store user info in request state for tools to access if needed
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                {"error": "invalid_token", "error_description": "Token has expired"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self.audience}", error="invalid_token"'}
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            return JSONResponse(
                {"error": "invalid_token", "error_description": "Token validation failed"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self.audience}", error="invalid_token"'}
            )

        return await call_next(request)


# Create FastMCP server (stateless_http set via FASTMCP_STATELESS_HTTP env var)
mcp = FastMCP("PCO Services MCP Server")


# ============== PCO Tools ==============

@mcp.tool()
def get_service_types() -> list:
    """Fetch a list of service types from Planning Center Online."""
    response = pco.get('/services/v2/service_types')
    return response['data']


@mcp.tool()
def get_plans(service_type_id: str) -> list:
    """Fetch a list of plans for a specific service type."""
    response = pco.get(f'/services/v2/service_types/{service_type_id}/plans?order=-updated_at')
    return response['data']


@mcp.tool()
def get_plan_items(plan_id: str) -> list:
    """Fetch a list of items for a specific plan."""
    response = pco.get(f'/services/v2/plans/{plan_id}/items')
    return response['data']


@mcp.tool()
def get_plan_team_members(plan_id: str) -> list:
    """Fetch a list of team members for a specific plan."""
    response = pco.get(f'/services/v2/plans/{plan_id}/team_members')
    return response['data']


@mcp.tool()
def get_songs() -> list:
    """Fetch a list of songs from Planning Center Online."""
    response = pco.get('/services/v2/songs?per_page=200&where[hidden]=false')
    return response['data']


@mcp.tool()
def get_all_arrangements_for_song(song_id: str) -> list:
    """Get all arrangements for a particular song."""
    response = pco.get(f'/services/v2/songs/{song_id}/arrangements')
    return response['data']


@mcp.tool()
def get_arrangement_for_song(song_id: str, arrangement_id: str) -> list:
    """Get information for a particular arrangement."""
    response = pco.get(f'/services/v2/songs/{song_id}/arrangements/{arrangement_id}')
    return response['data']


@mcp.tool()
def get_keys_for_arrangement_of_song(song_id: str, arrangement_id: str) -> list:
    """Get available keys for a particular arrangement."""
    response = pco.get(f'/services/v2/songs/{song_id}/arrangements/{arrangement_id}/keys')
    return response['data']


@mcp.tool()
def create_song(title: str, ccli: str = None) -> dict:
    """Create a new song in Planning Center Online."""
    attributes = {"title": title}
    if ccli:
        attributes["ccli_number"] = ccli
    body = pco.template('Song', attributes)
    response = pco.post('/services/v2/songs', body)
    return response['data']


@mcp.tool()
def find_song_by_title(title: str) -> list:
    """Find songs by title."""
    response = pco.get(f'/services/v2/songs?where[title]={title}&where[hidden]=false')
    return response['data']


@mcp.tool()
def get_song(song_id: str) -> dict:
    """Fetch details for a specific song."""
    response = pco.get(f'/services/v2/songs/{song_id}')
    return response['data']


@mcp.tool()
def assign_tags_to_song(song_id: str, tag_names: list[str]) -> dict:
    """Assign tags to a specific song."""
    tag_groups_response = pco.get('/services/v2/tag_groups?include=tags&filter=song')
    included_tags = tag_groups_response.get('included', [])

    tag_data = []
    for tag_name in tag_names:
        for tag in included_tags:
            if tag['type'] == 'Tag' and tag['attributes']['name'].lower() == tag_name.lower():
                tag_data.append({"type": "Tag", "id": tag['id']})
                break

    if not tag_data:
        return {"success": False, "message": "No matching tags found"}

    body = {
        "data": {
            "type": "TagAssignment",
            "attributes": {},
            "relationships": {"tags": {"data": tag_data}}
        }
    }
    pco.post(f'/services/v2/songs/{song_id}/assign_tags', body)
    return {"success": True, "message": f"Successfully assigned {len(tag_data)} tag(s) to song {song_id}"}


@mcp.tool()
def find_songs_by_tags(tag_names: list[str]) -> list:
    """Find songs that have all of the specified tags."""
    tag_groups_response = pco.get('/services/v2/tag_groups?include=tags&filter=song')
    included_tags = tag_groups_response.get('included', [])

    tag_ids = []
    for tag_name in tag_names:
        for tag in included_tags:
            if tag['type'] == 'Tag' and tag['attributes']['name'].lower() == tag_name.lower():
                tag_ids.append(tag['id'])
                break

    if not tag_ids:
        return []

    tag_filters = '&'.join([f'where[song_tag_ids]={tag_id}' for tag_id in tag_ids])
    response = pco.get(f'/services/v2/songs?per_page=200&where[hidden]=false&{tag_filters}')
    return response['data']


# ============== Application Setup ==============

def create_app() -> Starlette:
    """Create the Starlette application with Auth0 authentication."""

    # Create the MCP HTTP app once - its lifespan manages the session
    mcp_app = mcp.http_app()

    # Get lifespan - use .lifespan if available (fastmcp 2.4+), fallback to router.lifespan_context
    mcp_lifespan = getattr(mcp_app, "lifespan", None) or mcp_app.router.lifespan_context

    # Check if Auth0 is configured
    if not all([AUTH0_DOMAIN, AUTH0_AUDIENCE, BASE_URL]):
        logger.warning("Auth0 not configured - running without authentication")
        return Starlette(
            routes=[Mount("/mcp", app=mcp_app)],
            lifespan=mcp_lifespan,
        )

    logger.info(f"Auth0 configured: domain={AUTH0_DOMAIN}, audience={AUTH0_AUDIENCE}")

    # Create OAuth protected resource metadata routes
    metadata_routes = create_protected_resource_routes(
        resource_url=AUTH0_AUDIENCE,
        authorization_servers=[f"https://{AUTH0_DOMAIN}"],
        scopes_supported=["openid", "profile", "email"],
        resource_name="PCO Services MCP Server",
    )
    metadata_router = Router(routes=metadata_routes)

    # Auth middleware
    auth_middleware = [Middleware(Auth0Middleware, domain=AUTH0_DOMAIN, audience=AUTH0_AUDIENCE)]

    return Starlette(
        routes=[
            # OAuth metadata (no auth required)
            Mount("/", app=metadata_router),
            # MCP endpoint (auth required)
            Mount("/mcp", app=mcp_app, middleware=auth_middleware),
        ],
        lifespan=mcp_lifespan,
    )


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
