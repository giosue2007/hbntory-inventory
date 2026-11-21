#!/usr/bin/env python3
"""
Manual test of the Product MCP tools, before plugging them into the AI.

It starts mcp_server/product_server.py over stdio, like an MCP client
(an AI agent) would, lists the tools and calls them in 6 cases:
    1. list every product          4. unknown product id
    2. list one category           5. invalid product id
    3. details of one product      6. Product API down
The mock Product API must be running on PRODUCT_API_URL (port 9000).

Usage (from the project folder):
    python3 scripts/test_mcp_tools.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def server(api_url=None):
    """
    Describe how to start the MCP server, optionally on another API URL.
    """
    env = dict(os.environ)
    if api_url:
        env["PRODUCT_API_URL"] = api_url
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.product_server", "--stdio"], env=env)


async def call(session, title, tool, arguments):
    """
    Call one tool and print its structured result.
    """
    result = await session.call_tool(tool, arguments)
    data = result.structuredContent
    if data and data.get("count", 0) > 3:
        data = dict(data, products=data["products"][:3] + ["..."])
    shown = json.dumps(arguments, ensure_ascii=False)
    print(f"\n--- {title}: {tool}({shown})")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return result.structuredContent


async def main():
    """
    Run the 6 cases and print a summary.
    """
    checks = []
    async with stdio_client(server()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", ", ".join(t.name for t in tools.tools))
            r = await call(session, "1", "list_products", {})
            checks.append(r["ok"] and r["count"] > 0)
            r = await call(session, "2", "list_products",
                           {"category": "audio"})
            checks.append(r["ok"] and all(
                p["category"] == "Audio" for p in r["products"]))
            r = await call(session, "3", "get_product_details",
                           {"product_id": "6"})
            checks.append(r["ok"] and r["product"]["id"] == "6")
            r = await call(session, "4", "get_product_details",
                           {"product_id": "999"})
            checks.append(r["error"]["code"] == "PRODUCT_NOT_FOUND")
            r = await call(session, "5", "get_product_details",
                           {"product_id": "../admin"})
            checks.append(r["error"]["code"] == "INVALID_INPUT")
    async with stdio_client(server("http://127.0.0.1:9")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await call(session, "6 (API down)", "get_product_details",
                           {"product_id": "6"})
            checks.append(r["error"]["code"] == "PRODUCT_API_UNAVAILABLE")
    print(f"\n{sum(checks)} / {len(checks)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
