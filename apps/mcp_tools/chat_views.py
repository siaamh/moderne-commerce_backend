"""
POST /api/v1/chat/

Conversational shopping assistant endpoint.
Authenticates the customer, runs an LLM with all 13 MCP tools,
and returns the assistant reply plus any structured tool results.
"""
import json
import logging

from django.conf import settings
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.mcp_tools.tools.products import get_product_details, search_products
from apps.mcp_tools.tools.discovery import (
    get_active_offers,
    get_featured_products,
    list_categories,
    search_brands,
)
from apps.mcp_tools.tools.cart import (
    add_to_cart,
    get_cart,
    remove_from_cart,
    update_cart_item,
)
from apps.mcp_tools.tools.orders import (
    create_order,
    get_my_orders,
    get_order_details,
)

logger = logging.getLogger("mcp_tools.chat")

# ---------------------------------------------------------------------------
# Tool definitions (sent to LLM)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search the product catalog by name, category, brand, price range, "
                "or discount status. Use for any request to find, browse or search products."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search in product name/description"},
                    "brand_slug": {"type": "string", "description": "Brand slug to filter by"},
                    "category_slug": {"type": "string", "description": "Category slug (matches subcategories too)"},
                    "min_price": {"type": "number", "description": "Minimum price in BDT"},
                    "max_price": {"type": "number", "description": "Maximum price in BDT"},
                    "discounted_only": {"type": "boolean", "description": "Return only currently discounted products"},
                    "featured_only": {"type": "boolean", "description": "Return only featured/curated products"},
                    "limit": {"type": "integer", "description": "Max results (1-20, default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details for one product including description, pricing, stock, brand, and current offers. Use when the user asks about a specific product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product database ID"},
                    "slug": {"type": "string", "description": "Product URL slug"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "List product categories and subcategories. Use when the user asks what categories or product types are available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parent_id": {"type": "integer", "description": "Get subcategories of this parent category ID"},
                    "include_subcategories": {"type": "boolean", "description": "Include nested subcategories (default true)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_brands",
            "description": "Search or list available brands with product counts. Use when the user mentions a brand name or asks to browse by brand. Then use search_products with brand_slug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Brand name to search"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_featured_products",
            "description": "Get curated featured products. Use when the user asks for recommendations, top picks, bestsellers, or featured items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (1-20, default 8)"},
                    "category_slug": {"type": "string", "description": "Filter by category"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_offers",
            "description": "Get current limited-time discount offers and deals. Use when the user asks about sales, promotions, or what's discounted right now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_slug": {"type": "string", "description": "Filter by category"},
                    "brand_slug": {"type": "string", "description": "Filter by brand"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart",
            "description": "Get the customer's current shopping cart with items, quantities, current prices (including discounts), and total. Always call this before checkout.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the customer's cart. Validates stock availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID to add"},
                    "quantity": {"type": "integer", "description": "Number of units to add"},
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_cart_item",
            "description": "Change the quantity of an item already in the cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_item_id": {"type": "integer", "description": "Cart item ID (from get_cart response)"},
                    "quantity": {"type": "integer", "description": "New quantity"},
                },
                "required": ["cart_item_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Remove an item from the customer's cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_item_id": {"type": "integer", "description": "Cart item ID to remove"},
                },
                "required": ["cart_item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_orders",
            "description": "Get the customer's order history. Use when the user asks about past orders, recent purchases, or order status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter: pending|confirmed|shipped|delivered|cancelled"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Get full details for a specific order including items, prices and shipping info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {"type": "string", "description": "Order number (e.g. 'ABC123456789')"},
                    "order_id": {"type": "integer", "description": "Order database ID"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": (
                "Place an order using the customer's cart. "
                "ONLY call this AFTER: "
                "(1) calling get_cart to see current items, "
                "(2) presenting a clear summary of items, prices, delivery fee (৳60) and total, "
                "(3) the customer explicitly confirms they want to place the order. "
                "Set customer_confirmation=true only after that explicit confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string", "description": "Recipient's full name"},
                    "phone": {"type": "string", "description": "Contact phone number"},
                    "delivery_address": {"type": "string", "description": "Full delivery address"},
                    "payment_method": {"type": "string", "description": "Must be: cash_on_delivery"},
                    "customer_confirmation": {"type": "boolean", "description": "Must be true — confirms the customer has agreed to place the order"},
                },
                "required": ["full_name", "phone", "delivery_address", "payment_method", "customer_confirmation"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, args: dict, user) -> dict:
    """Route a tool call to the correct Python function."""
    # Tools that require authentication
    PRIVATE_TOOLS = {
        "get_cart", "add_to_cart", "update_cart_item", "remove_from_cart",
        "get_my_orders", "get_order_details", "create_order",
    }

    if name in PRIVATE_TOOLS and user is None:
        return {
            "status": "error",
            "code": "UNAUTHORIZED",
            "message": "Please log in to use this feature.",
        }

    try:
        if name == "search_products":
            return search_products(**args)
        elif name == "get_product_details":
            return get_product_details(**args)
        elif name == "list_categories":
            return list_categories(**args)
        elif name == "search_brands":
            return search_brands(**args)
        elif name == "get_featured_products":
            return get_featured_products(**args)
        elif name == "get_active_offers":
            return get_active_offers(**args)
        elif name == "get_cart":
            return get_cart(user)
        elif name == "add_to_cart":
            return add_to_cart(user, **args)
        elif name == "update_cart_item":
            return update_cart_item(user, **args)
        elif name == "remove_from_cart":
            return remove_from_cart(user, **args)
        elif name == "get_my_orders":
            return get_my_orders(user, **args)
        elif name == "get_order_details":
            return get_order_details(user, **args)
        elif name == "create_order":
            return create_order(user, **args)
        else:
            return {"status": "error", "code": "UNKNOWN_TOOL", "message": f"Unknown tool: {name}"}
    except TypeError as exc:
        logger.warning("Tool %s bad arguments %s: %s", name, args, exc)
        return {"status": "error", "code": "INVALID_INPUT", "message": str(exc)}
    except Exception as exc:
        logger.error("Tool %s crashed: %s", name, exc, exc_info=True)
        return {"status": "error", "code": "TOOL_ERROR", "message": "Tool execution failed."}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful shopping assistant for VERDANT, a premium e-commerce store.
You help customers find products, manage their cart, and place orders.

RULES:
- Always use the provided tools to fetch real data. Never invent product names, IDs, prices, or stock levels.
- For product searches, use search_products. For specific products, use get_product_details.
- For checkout: ALWAYS call get_cart first, present a clear summary to the customer, wait for explicit confirmation, then call create_order with customer_confirmation=true.
- Prices are always in BDT (৳). Delivery fee is ৳60.00 for all orders.
- Only cash_on_delivery is supported as a payment method.
- If a tool returns an error, explain it clearly to the customer.
- Be concise and helpful. Format prices clearly with the ৳ symbol.
- You can make multiple sequential tool calls when needed (e.g. search brands then search products).
"""

# ---------------------------------------------------------------------------
# LLM runner
# ---------------------------------------------------------------------------

def _run_openai(messages: list, user) -> tuple[str, list]:
    """
    Run conversation via OpenRouter (OpenAI-compatible).
    Falls back to direct OpenAI if OPENROUTER_API_KEY is not set.
    """
    import openai

    openrouter_key = getattr(settings, "OPENROUTER_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    if openrouter_key:
        client = openai.OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://localhost:8742"),
                "X-Title": getattr(settings, "OPENROUTER_SITE_NAME", "VERDANT Shopping Assistant"),
            },
        )
        model = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini")
    else:
        client = openai.OpenAI(api_key=openai_key)
        model = "gpt-4o-mini"

    tool_results = []

    for _ in range(8):  # max 8 LLM turns (for multi-step tool calls)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            timeout=settings.MCP_TIMEOUT,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or "", tool_results

        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each tool call
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = dispatch_tool(tc.function.name, args, user)
            tool_results.append({"tool": tc.function.name, "args": args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "I've completed the requested actions.", tool_results


def _run_anthropic(messages: list, user) -> tuple[str, list]:
    """Run conversation with Anthropic Claude. Returns (reply_text, tool_results)."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    tool_results = []

    # Convert OpenAI-style tools to Anthropic format
    anthropic_tools = []
    for t in TOOL_DEFINITIONS:
        f = t["function"]
        anthropic_tools.append({
            "name": f["name"],
            "description": f["description"],
            "input_schema": f["parameters"],
        })

    # Separate system message from history
    system = SYSTEM_PROMPT
    claude_messages = [m for m in messages if m["role"] != "system"]

    for _ in range(8):
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2048,
            system=system,
            messages=claude_messages,
            tools=anthropic_tools,
        )

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return text, tool_results

        if response.stop_reason == "tool_use":
            claude_messages.append({"role": "assistant", "content": response.content})
            tool_result_blocks = []
            for block in response.content:
                if block.type == "tool_use":
                    result = dispatch_tool(block.name, block.input, user)
                    tool_results.append({"tool": block.name, "args": block.input, "result": result})
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            claude_messages.append({"role": "user", "content": tool_result_blocks})

    return "I've completed the requested actions.", tool_results


# ---------------------------------------------------------------------------
# Django view
# ---------------------------------------------------------------------------

class ChatView(APIView):
    """
    Public endpoint — authentication is optional.
    - Unauthenticated users can browse products, categories, brands and offers.
    - Authenticated customers can also use cart and order tools.
    Private tools return a friendly "please log in" message for guests.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        # request.user is an AnonymousUser when no token is supplied — that's fine.
        user = request.user if request.user.is_authenticated else None
        message = request.data.get("message", "").strip()
        conversation_history = request.data.get("conversation_history", [])

        if not message:
            return Response({"error": "message is required."}, status=400)

        # Build messages list
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Include last 10 turns of history
        for entry in conversation_history[-10:]:
            role = entry.get("role")
            content = entry.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        # Pick LLM provider — OpenRouter takes priority, then OpenAI, then Anthropic
        openrouter_key = getattr(settings, "OPENROUTER_API_KEY", "")
        openai_key = getattr(settings, "OPENAI_API_KEY", "")
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "")

        tool_results = []
        reply = ""

        try:
            if openrouter_key or openai_key:
                reply, tool_results = _run_openai(messages, user)
            elif anthropic_key:
                reply, tool_results = _run_anthropic(messages, user)
            else:
                return Response(
                    {"error": "No AI provider configured. Set OPENROUTER_API_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY."},
                    status=503,
                )
        except Exception as exc:
            user_id = user.pk if user else "anonymous"
            logger.error("Chat LLM error for user %s: %s", user_id, exc, exc_info=True)
            return Response({"error": "AI service temporarily unavailable."}, status=503)

        # Extract structured data for the frontend
        products = []
        cart_update = None
        order_result = None

        for tr in tool_results:
            result = tr.get("result", {})
            if result.get("status") == "success":
                data = result.get("data", {})
                if tr["tool"] in ("search_products", "get_featured_products"):
                    products.extend(data.get("products", []))
                elif tr["tool"] == "get_product_details":
                    products.append(data)
                elif tr["tool"] in ("get_cart", "add_to_cart", "update_cart_item", "remove_from_cart"):
                    cart_update = data.get("cart", data)
                elif tr["tool"] == "create_order":
                    order_result = data

        return Response({
            "reply": reply,
            "tool_calls": [
                {"tool": tr["tool"], "status": tr["result"].get("status")}
                for tr in tool_results
            ],
            "products": products[:12],  # Cap at 12 for UI
            "cart_update": cart_update,
            "order_result": order_result,
        })
