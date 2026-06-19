from typing import Dict, List

from pydantic import BaseModel, Field


class DailySummary(BaseModel):
    date: str
    sales: Dict[str, float] = {}
    expenses: Dict[str, float] = {}
    net_profit: float = 0
    payment_methods: Dict[str, float] = {}
    repairs_completed: int = 0
    new_customers: int = 0
    total_repair_revenue: float = 0
    total_manual_sales: float = 0
    total_expenses: float = 0


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_revenue: float = 0
    total_expenses: float = 0
    net_profit: float = 0
    repairs_completed: int = 0
    repairs_received: int = 0
    new_customers: int = 0
    daily_breakdown: List[DailySummary] = []
    payment_methods: Dict[str, float] = {}
    expense_categories: Dict[str, float] = {}


class ProfitLossItem(BaseModel):
    date: str
    revenue: float = 0
    expenses: float = 0
    net: float = 0


class ProfitLossReport(BaseModel):
    start_date: str
    end_date: str
    total_revenue: float = 0
    total_expenses: float = 0
    net_profit: float = 0
    items: List[ProfitLossItem] = []
    expense_breakdown: Dict[str, float] = {}
    revenue_breakdown: Dict[str, float] = {}
