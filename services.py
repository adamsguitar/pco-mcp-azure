"""
PCO Services MCP Server with Auth0 authentication.
Uses FastMCP's built-in Auth0Provider for DCR-compatible OAuth.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.auth0 import Auth0Provider
from pypco import PCO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", "8080"))

# Initialize PCO client
pco = PCO(
    application_id=os.getenv("PCO_APPLICATION_ID"),
    secret=os.getenv("PCO_SECRET_KEY")
)

# Set up Auth0 authentication if configured
auth = None
if all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_AUDIENCE, BASE_URL]):
    logger.info(f"Auth0 configured: domain={AUTH0_DOMAIN}, audience={AUTH0_AUDIENCE}")
    auth = Auth0Provider(
        config_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
        audience=AUTH0_AUDIENCE,
        base_url=BASE_URL,
    )
else:
    logger.warning("Auth0 not fully configured - running without authentication")

# Create FastMCP server with Auth0 authentication
mcp = FastMCP("PCO Services MCP Server", auth=auth)


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


# ============== Application Entry Point ==============

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=PORT)
