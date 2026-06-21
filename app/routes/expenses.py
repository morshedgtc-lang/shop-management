from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseCategoryCreate,
    ExpenseCategoryResponse, ExpenseResponse,
)
from app.utils.auth import get_current_user
from app.utils.permissions import require_admin, require_warehouse_or_admin

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("", response_model=dict)
async def list_expenses(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = []
    if date_from:
        filters.append(Expense.date >= date_from)
    if date_to:
        filters.append(Expense.date <= date_to)
    if category_id:
        filters.append(Expense.category_id == category_id)
    total = (await db.execute(select(sqlfunc.count(Expense.id)).where(*filters))).scalar() or 0
    expenses = (
        (await db.execute(select(Expense).where(*filters).order_by(Expense.date.desc()).offset((page - 1) * limit).limit(limit)))
        .scalars()
        .all()
    )
    items = []
    cat_ids = list(set(e.category_id for e in expenses))
    cat_map = {}
    if cat_ids:
        cats = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id.in_(cat_ids)))).scalars().all()
        cat_map = {c.id: c.name for c in cats}
    for e in expenses:
        items.append(
            ExpenseResponse(
                id=e.id, date=e.date, amount=e.amount, currency=e.currency,
                category_id=e.category_id, category_name=cat_map.get(e.category_id, ""),
                note=e.note, created_by=e.created_by, created_at=e.created_at,
            )
        )
    return {
        "items": items, "total": total, "page": page,
        "limit": limit, "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    cat = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == data.category_id))).scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense category not found")
    expense_date = data.date or date.today().isoformat()
    expense = Expense(
        amount=data.amount, category_id=data.category_id,
        currency=data.currency, note=data.note,
        date=expense_date, created_by=current_user.id,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return ExpenseResponse(
        id=expense.id, date=expense.date, amount=expense.amount,
        currency=expense.currency, category_id=expense.category_id,
        category_name=cat.name, note=expense.note,
        created_by=expense.created_by, created_at=expense.created_at,
    )


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    db=Depends(get_db),
    current_user=Depends(require_warehouse_or_admin),
):
    expense = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    await db.commit()
    await db.refresh(expense)
    cat = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == expense.category_id))).scalar_one_or_none()
    return ExpenseResponse(
        id=expense.id, date=expense.date, amount=expense.amount,
        currency=expense.currency, category_id=expense.category_id,
        category_name=cat.name if cat else "", note=expense.note,
        created_by=expense.created_by, created_at=expense.created_at,
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    expense = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    await db.delete(expense)
    await db.commit()


@router.get("/categories", response_model=list[ExpenseCategoryResponse])
async def list_expense_categories(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (await db.execute(select(ExpenseCategory))).scalars().all()
    return rows


@router.post("/categories", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_expense_category(
    data: ExpenseCategoryCreate,
    db=Depends(get_db),
    current_user=Depends(require_admin),
):
    existing = (await db.execute(select(ExpenseCategory).where(ExpenseCategory.name == data.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category with this name already exists")
    category = ExpenseCategory(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
