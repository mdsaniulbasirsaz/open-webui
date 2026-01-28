from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.token_budgets import TokenBudgetModel, TokenBudgets
from open_webui.utils.auth import get_admin_user
from open_webui.utils.token_budget import TokenBudgetService, TokenBudgetStatusModel

router = APIRouter()


class UpsertTokenBudgetForm(BaseModel):
    limit_tokens: int = Field(..., ge=0)
    enabled: bool = True
    timezone: Optional[str] = None


@router.put(
    "/admin/token-budgets/users/{user_id}",
    response_model=TokenBudgetModel,
)
async def upsert_user_token_budget(
    user_id: str,
    form_data: UpsertTokenBudgetForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    return TokenBudgets.upsert_budget(
        user_id=user_id,
        created_by=user.id,
        limit_tokens=form_data.limit_tokens,
        enabled=form_data.enabled,
        timezone=form_data.timezone,
        window_type="monthly",
        db=db,
    )


@router.get(
    "/admin/token-budgets/users/{user_id}/status",
    response_model=TokenBudgetStatusModel,
)
async def get_user_token_budget_status(
    user_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    status = TokenBudgetService.get_status(user_id=user_id, db=db)
    if status is None:
        # Keep response model stable: treat as "no budget configured"
        return TokenBudgetStatusModel(
            user_id=user_id,
            enabled=False,
            window_type="monthly",
            timezone=None,
            window_start=0,
            reset_at=0,
            limit_tokens=0,
            used_tokens=0,
            reserved_tokens=0,
            remaining_tokens=0,
        )
    return status


@router.get(
    "/admin/token-budgets",
    response_model=list[TokenBudgetModel],
)
async def list_token_budgets(
    query: Optional[str] = Query(None, description="Filter by user_id (substring match)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    from open_webui.models.token_budgets import TokenBudget

    query_obj = db.query(TokenBudget)
    if query:
        query_obj = query_obj.filter(TokenBudget.user_id.ilike(f"%{query}%"))
    rows = query_obj.order_by(TokenBudget.user_id.asc()).offset(offset).limit(limit).all()
    return [TokenBudgetModel.model_validate(r) for r in rows]
