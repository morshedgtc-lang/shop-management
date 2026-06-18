from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryResponse,
    ExpenseResponse,
)
from app.utils.auth import get_current_user, require_admin, require_manager_or_admin

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("", response_model=dict)
def list_expenses(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Expense)
    if date_from:
        query = query.filter(Expense.date >= date_from)
    if date_to:
        query = query.filter(Expense.date <= date_to)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    total = query.count()
    expenses = (
        query.order_by(Expense.date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    items = []
    for e in expenses:
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first()
        items.append(
            ExpenseResponse(
                id=e.id,
                date=e.date,
                amount=e.amount,
                currency=e.currency,
                category_id=e.category_id,
                category_name=cat.name if cat else "",
                note=e.note,
                created_by=e.created_by,
                created_at=e.created_at,
            )
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == data.category_id).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense category not found"
        )
    expense_date = data.date or date.today().isoformat()
    expense = Expense(
        amount=data.amount,
        category_id=data.category_id,
        currency=data.currency,
        note=data.note,
        date=expense_date,
        created_by=current_user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return ExpenseResponse(
        id=expense.id,
        date=expense.date,
        amount=expense.amount,
        currency=expense.currency,
        category_id=expense.category_id,
        category_name=cat.name,
        note=expense.note,
        created_by=expense.created_by,
        created_at=expense.created_at,
    )


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == expense.category_id).first()
    return ExpenseResponse(
        id=expense.id,
        date=expense.date,
        amount=expense.amount,
        currency=expense.currency,
        category_id=expense.category_id,
        category_name=cat.name if cat else "",
        note=expense.note,
        created_by=expense.created_by,
        created_at=expense.created_at,
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )
    db.delete(expense)
    db.commit()


@router.get("/categories", response_model=list[ExpenseCategoryResponse])
def list_expense_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ExpenseCategory).all()


@router.post(
    "/categories",
    response_model=ExpenseCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense_category(
    data: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = (
        db.query(ExpenseCategory)
        .filter(ExpenseCategory.name == data.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )
    category = ExpenseCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
