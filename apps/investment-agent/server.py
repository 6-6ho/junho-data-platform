"""Investment Agent MCP Server — 투자 기준, 인사이트 메모, 시장 데이터."""
import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource

from tools.criteria import save_criteria, list_criteria, get_criteria, delete_criteria
from tools.memos import save_memo, search_memos, recent_memos
from tools.market import get_market_summary, screen_coins, get_coin_detail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

server = Server("investment-agent")


# === Tools ===

@server.list_tools()
async def handle_list_tools():
    return [
        # 투자 기준
        Tool(
            name="save_criteria",
            description="투자 기준을 저장하거나 수정합니다. 카테고리: entry(진입), exit(청산), risk(리스크 관리), general(일반)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "기준 이름 (고유)"},
                    "content": {"type": "string", "description": "기준 내용"},
                    "category": {
                        "type": "string",
                        "enum": ["entry", "exit", "risk", "general"],
                        "default": "general",
                    },
                },
                "required": ["name", "content"],
            },
        ),
        Tool(
            name="list_criteria",
            description="저장된 투자 기준 목록을 조회합니다. 카테고리로 필터 가능.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["entry", "exit", "risk", "general"],
                        "description": "필터할 카테고리 (생략 시 전체)",
                    },
                },
            },
        ),
        Tool(
            name="get_criteria",
            description="특정 투자 기준의 상세 내용을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "기준 이름"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="delete_criteria",
            description="투자 기준을 삭제합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "삭제할 기준 이름"},
                },
                "required": ["name"],
            },
        ),
        # 인사이트 메모
        Tool(
            name="save_memo",
            description="투자/경제 인사이트 메모를 저장합니다. 자동 태그 + 벡터 임베딩.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "메모 내용"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "수동 태그 (자동 태그에 추가)",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_memos",
            description="저장된 메모를 벡터 유사도로 검색합니다. 관련 인사이트를 찾을 때 사용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 질의"},
                    "limit": {"type": "integer", "default": 5, "description": "반환 개수"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="recent_memos",
            description="최근 저장된 메모를 시간순으로 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10, "description": "반환 개수"},
                },
            },
        ),
        # 시장 데이터
        Tool(
            name="get_market_summary",
            description="현재 시장 상태 요약: 변동률 상위 코인, 최근 whale 에피소드, BTC 호가 깊이.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="screen_coins",
            description="종목 스크리닝: junk 제외, 거래량 상위, 최근 변동 종목 필터. 투자 기준 참조 가능.",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {
                        "type": "string",
                        "description": "참조할 투자 기준 이름 (생략 가능)",
                    },
                },
            },
        ),
        Tool(
            name="get_coin_detail",
            description="특정 코인의 상세 정보: 가격, 변동률, 스크리너 정보, 최근 movers 이벤트.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "코인 심볼 (예: BTC, ETH)"},
                },
                "required": ["symbol"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    handlers = {
        "save_criteria": lambda args: save_criteria(
            args["name"], args["content"], args.get("category", "general")
        ),
        "list_criteria": lambda args: list_criteria(args.get("category")),
        "get_criteria": lambda args: get_criteria(args["name"]),
        "delete_criteria": lambda args: delete_criteria(args["name"]),
        "save_memo": lambda args: save_memo(
            args["content"], args.get("tags"), "mcp"
        ),
        "search_memos": lambda args: search_memos(
            args["query"], args.get("limit", 5)
        ),
        "recent_memos": lambda args: recent_memos(args.get("limit", 10)),
        "get_market_summary": lambda args: get_market_summary(),
        "screen_coins": lambda args: screen_coins(args.get("criteria_name")),
        "get_coin_detail": lambda args: get_coin_detail(args["symbol"]),
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = handler(arguments or {})
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


# === Resources ===

@server.list_resources()
async def handle_list_resources():
    return [
        Resource(
            uri="investment://criteria",
            name="투자 기준 목록",
            description="저장된 모든 투자 기준",
            mimeType="application/json",
        ),
        Resource(
            uri="investment://memos/recent",
            name="최근 메모",
            description="최근 인사이트 메모 10건",
            mimeType="application/json",
        ),
        Resource(
            uri="investment://market/overview",
            name="시장 요약",
            description="현재 시장 상태 요약",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str):
    if str(uri) == "investment://criteria":
        return list_criteria()
    elif str(uri) == "investment://memos/recent":
        return recent_memos(10)
    elif str(uri) == "investment://market/overview":
        return get_market_summary()
    else:
        return f"Unknown resource: {uri}"


# === Main ===

async def main():
    logger.info("Investment Agent MCP Server 시작")
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
