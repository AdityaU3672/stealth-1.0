from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from src.database import get_db
from src.middleware.auth import get_current_org, get_current_user
from src.models.connector import Connector
from src.schemas.common import ApiResponse
from src.schemas.trigger import (
    TriggerConnectorOption,
    TriggerCreate,
    TriggerDetail,
    TriggerRead,
    TriggerUpdate,
)
from src.services.triggers import trigger_service

router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])


def _callback_url(request: Request, plugin_type: str, webhook_token: str) -> str:
    if plugin_type == "slack":
        return str(request.base_url).rstrip("/") + "/api/v1/triggers/webhooks/slack"
    return str(request.base_url).rstrip("/") + f"/api/v1/triggers/webhooks/{plugin_type}/{webhook_token}"


def _slack_workspace_id(payload: dict) -> str | None:
    candidates = [
        payload.get("team_id"),
        ((payload.get("authorizations") or [{}])[0]).get("team_id")
        if isinstance(payload.get("authorizations"), list) and payload.get("authorizations")
        else None,
        ((payload.get("event_context") or "").split("T", 1)[1].split("-", 1)[0])
        if isinstance(payload.get("event_context"), str) and "T" in payload.get("event_context", "")
        else None,
    ]
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return None


async def _resolve_connector(
    db: AsyncSession,
    plugin_type: str,
    webhook_token: str | None,
    payload: dict | None = None,
) -> Connector | None:
    if webhook_token:
        connector_row = await db.execute(
            select(Connector).where(
                Connector.webhook_token == webhook_token,
                Connector.type == plugin_type,
                Connector.enabled.is_(True),
            )
        )
        return connector_row.scalar_one_or_none()

    if plugin_type != "slack" or payload is None:
        return None

    workspace_id = _slack_workspace_id(payload)
    if not workspace_id:
        return None

    connector_row = await db.execute(
        select(Connector)
        .where(
            Connector.type == "slack",
            Connector.enabled.is_(True),
            Connector.credentials["team_id"].astext == workspace_id,
        )
        .order_by(Connector.updated_at.desc(), Connector.created_at.desc())
    )
    return connector_row.scalars().first()


@router.get("/config", response_model=ApiResponse[list[TriggerConnectorOption]])
async def trigger_config(
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    options = await trigger_service.list_connector_options(db, org_id)
    return ApiResponse(data=options)


@router.get("", response_model=ApiResponse[list[TriggerRead]])
async def list_triggers(
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(data=await trigger_service.list_triggers(db, org_id))


@router.post("", response_model=ApiResponse[TriggerRead])
async def create_trigger(
    payload: TriggerCreate,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connector_row = await db.execute(
        select(Connector).where(
            Connector.id == payload.connector_id,
            Connector.organization_id == user.organization_id,
        )
    )
    connector = connector_row.scalar_one_or_none()
    if connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    try:
        trigger = await trigger_service.create_trigger(
            db,
            org_id=str(user.organization_id),
            user_id=str(user.id),
            connector_id=payload.connector_id,
            natural_language_description=payload.natural_language_description,
            scope=payload.scope,
            buffer_config=payload.buffer_config.model_dump(),
            match_config=payload.match_config.model_dump(),
            status=payload.status,
            callback_url=_callback_url(request, connector.type, connector.webhook_token),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ApiResponse(data=trigger)


@router.get("/{trigger_id}", response_model=ApiResponse[TriggerDetail])
async def get_trigger(
    trigger_id: UUID,
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    detail = await trigger_service.get_trigger_detail(db, org_id, trigger_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return ApiResponse(data=detail)


@router.patch("/{trigger_id}", response_model=ApiResponse[TriggerRead])
async def update_trigger(
    trigger_id: UUID,
    payload: TriggerUpdate,
    request: Request,
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    try:
        existing = await trigger_service.get_trigger_detail(db, org_id, trigger_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
        connector_row = await db.execute(
            select(Connector).where(
                Connector.id == existing.trigger.connector_id,
                Connector.organization_id == UUID(org_id),
            )
        )
        connector = connector_row.scalar_one_or_none()
        if connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
        trigger = await trigger_service.update_trigger(
            db,
            org_id=org_id,
            trigger_id=trigger_id,
            natural_language_description=payload.natural_language_description,
            scope=payload.scope,
            buffer_config=payload.buffer_config.model_dump() if payload.buffer_config else None,
            match_config=payload.match_config.model_dump() if payload.match_config else None,
            status=payload.status,
            callback_url=_callback_url(request, existing.trigger.plugin_type, connector.webhook_token),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return ApiResponse(data=trigger)


@router.delete("/{trigger_id}", response_model=ApiResponse[dict])
async def delete_trigger(
    trigger_id: UUID,
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    deleted = await trigger_service.delete_trigger(db, org_id, trigger_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return ApiResponse(data={"deleted": True})


@router.post("/{trigger_id}/pause", response_model=ApiResponse[TriggerRead])
async def pause_trigger(
    trigger_id: UUID,
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    trigger = await trigger_service.set_trigger_status(db, org_id, trigger_id, "paused")
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return ApiResponse(data=trigger)


@router.post("/{trigger_id}/resume", response_model=ApiResponse[TriggerRead])
async def resume_trigger(
    trigger_id: UUID,
    org_id: str = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    trigger = await trigger_service.set_trigger_status(db, org_id, trigger_id, "active")
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return ApiResponse(data=trigger)


@router.post("/dispatch-due", response_model=ApiResponse[dict])
async def dispatch_due_buffers(org_id: str = Depends(get_current_org)):
    processed = await trigger_service.run_due_buffers_once(org_id=org_id)
    return ApiResponse(data={"processed": processed})


@router.post("/webhooks/slack")
@router.post("/webhooks/{plugin_type}/{webhook_token}")
async def receive_webhook(
    request: Request,
    plugin_type: str = "slack",
    webhook_token: str | None = None,
    db: AsyncSession = Depends(get_db),
    validation_token: str | None = Query(default=None, alias="validationToken"),
):
    if validation_token:
        return PlainTextResponse(content=validation_token)

    webhook_logger = structlog.get_logger("webhook")

    payload = await request.json()

    if plugin_type == "slack" and payload.get("type") == "url_verification":
        webhook_logger.info("webhook.url_verification", plugin_type=plugin_type)
        return {"challenge": payload.get("challenge")}

    connector = await _resolve_connector(db, plugin_type, webhook_token, payload)
    if connector is None:
        if plugin_type == "slack" and not webhook_token:
            webhook_logger.warning(
                "webhook.slack_workspace_not_found",
                plugin_type=plugin_type,
                workspace_id=_slack_workspace_id(payload),
            )
        else:
            webhook_logger.warning("webhook.invalid_token", plugin_type=plugin_type)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid webhook URL")

    webhook_logger.info(
        "webhook.received",
        plugin_type=plugin_type,
        organization_id=str(connector.organization_id),
        payload_type=payload.get("type"),
        event_type=payload.get("event", {}).get("type") if isinstance(payload.get("event"), dict) else None,
    )

    # Slack retries after 3s if no response — ignore retries to prevent duplicates
    if request.headers.get("x-slack-retry-num"):
        return {"ok": True}

    try:
        result = await trigger_service.process_webhook(
            db,
            plugin_type=plugin_type,
            organization_id=str(connector.organization_id),
            payload=payload,
            headers={key.lower(): value for key, value in request.headers.items()},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, **result}
