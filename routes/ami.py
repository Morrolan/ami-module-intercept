"""Opt-in, bearer-authenticated AMI service module (separate from browser sessions)."""
import json
import time

from flask import Blueprint, Response, abort, jsonify, request, stream_with_context

from config import VERSION
from utils.ami import TOOLS, ami_origin, call_tool, iso, journal, token_valid
from utils.ami_features import features

ami_bp = Blueprint("ami", __name__)


@ami_bp.before_request
def authorize():
    if not ami_origin():
        abort(404)
    if request.endpoint not in ("ami.manifest", "ami.health"):
        if not token_valid(request.headers.get("Authorization", "")):
            return jsonify(error="Bearer token required"), 401, {"WWW-Authenticate": "Bearer"}


@ami_bp.get("/.well-known/ami-module.json")
def manifest():
    return jsonify({"contract": "1", "id": "intercept", "name": "Intercept", "version": VERSION,
                    "features": features(),
                    "description": "Radio receiver and decoder intelligence", "mcp": "/api/module/mcp",
                    "health": "/api/module/health", "events": "/api/module/events",
                    "auth": {"type": "token", "roles": ["admin"]},
                    "scopes": [{"id": "intercept.read", "description": "Read decoder health and sanitized contacts"}],
                    "ui": {"entry": "/?ami=1", "embed": True,
                           "session": "/api/module/session", "enter": "/ami/enter", "deepLinks": {
                        "aircraft": "/adsb/dashboard?ami=1", "vessels": "/ais/dashboard?ami=1"}},
                    "eventKinds": [{"id": "decoder-health", "label": "Decoder health", "adminOnly": True},
                                   {"id": "feed-gap", "label": "Data gaps (feeds gone quiet)", "adminOnly": True}]})


@ami_bp.post("/api/module/session")
def browser_session():
    from utils.ami_access import enabled_account, entry_tickets, mapped_account

    if not entry_tickets.rate_allowed():
        return jsonify(error="Too many requests"), 429, {"Retry-After": "60", "Cache-Control": "no-store"}
    request.max_content_length = 4096
    body = request.get_json(silent=True)
    username = mapped_account(body.get("user")) if isinstance(body, dict) else None
    if (not username or body.get("mfa") is not True
            or body.get("role") not in ("admin", "resident", "viewer")
            or not enabled_account(username)):
        return jsonify(error="not allowed"), 403, {"Cache-Control": "no-store"}
    return jsonify(ticket=entry_tickets.issue(username), expiresIn=60), 200, {"Cache-Control": "no-store"}


@ami_bp.get("/api/module/health")
def health():
    return jsonify(status="ok", module="intercept", version=VERSION, checkedAt=iso(), detail="Read-only module available")


@ami_bp.post("/api/module/mcp")
def mcp():
    request.max_content_length = 16384
    if request.content_length is not None and request.content_length > 16384:
        abort(413)
    msg = request.get_json(silent=True)
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return jsonify(jsonrpc="2.0", id=None, error={"code": -32600, "message": "Invalid request"})
    req_id = msg.get("id")
    if isinstance(req_id, (dict, list, bool)):
        return jsonify(jsonrpc="2.0", id=None, error={"code": -32600, "message": "Invalid id"})
    if "id" not in msg:
        return "", 202  # MCP notifications never produce a JSON-RPC response.
    method, params = msg["method"], msg.get("params", {})
    if not isinstance(params, dict):
        return jsonify(jsonrpc="2.0", id=req_id, error={"code": -32602, "message": "Invalid params"})
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "intercept", "version": VERSION}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            data = call_tool(params.get("name"), params.get("arguments", {}))
            result = {"structuredContent": data, "content": [{"type": "text", "text": json.dumps(data)}]}
        except ValueError:
            return jsonify(jsonrpc="2.0", id=req_id, error={"code": -32602, "message": "Invalid tool or arguments"})
    else:
        return jsonify(jsonrpc="2.0", id=req_id, error={"code": -32601, "message": "Method not found"})
    journal()  # Start the independent health sampler on first AMI connection.
    return jsonify(jsonrpc="2.0", id=req_id, result=result)


@ami_bp.get("/api/module/events")
def events():
    history = journal()
    cursor = request.headers.get("Last-Event-ID", "")
    if cursor:
        if not cursor.startswith("intercept:") or not cursor[10:].isascii() or not cursor[10:].isdigit() or len(cursor) > 30:
            abort(400)
        after = int(cursor[10:])
        if after > history.latest():
            abort(400)
    else:
        after = 0
    bearer = request.headers.get("Authorization", "")

    @stream_with_context
    def generate():
        nonlocal after
        while token_valid(bearer):  # A rotated or removed token also terminates existing streams.
            rows = history.recent(after, 100)
            for seq, event in rows:
                yield f"id: intercept:{seq}\nevent: ami-event\ndata: {json.dumps(event)}\n\n"
                after = seq
            yield ": heartbeat\n\n"
            time.sleep(15)
    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no"})
