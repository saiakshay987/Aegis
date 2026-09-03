"""
SQLAlchemy 2.0 Declarative Models for Aegis
Relational Schema: MCC Codes, Customers, Loans, Transactions, Interventions
Includes daily interest accrual tracking and MCC guardrails.
"""

from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, 
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MCCCode(Base):
    """
    Feature 2: Merchant Category Code Guardrail Table.
    Enforces validation of legitimate exogenous emergency shocks (e.g. medical surgery).
    """
    __tablename__ = "mcc_codes"

    code: Mapped[str] = mapped_column(String(4), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_shock_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="mcc_ref")

    def __repr__(self) -> str:
        return f"<MCCCode(code='{self.code}', category='{self.category_name}', shock_eligible={self.is_shock_eligible})>"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    archetype: Mapped[str] = mapped_column(String(30), nullable=False)  # HEALTHY, MEDICAL_SHOCK, VOLATILE_INCOME
    monthly_income_avg: Mapped[float] = mapped_column(Float, nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    loans: Mapped[List["Loan"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    interventions: Mapped[List["Intervention"]] = relationship(back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("archetype IN ('HEALTHY', 'MEDICAL_SHOCK', 'VOLATILE_INCOME')", name="check_archetype"),
        CheckConstraint("credit_score BETWEEN 300 AND 900", name="check_credit_score"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id='{self.id}', name='{self.first_name} {self.last_name}', archetype='{self.archetype}')>"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    principal_amount: Mapped[float] = mapped_column(Float, nullable=False)
    interest_rate_apr: Mapped[float] = mapped_column(Float, nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_emi: Mapped[float] = mapped_column(Float, nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    nach_mandate_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="loans")
    interventions: Mapped[List["Intervention"]] = relationship(back_populates="loan", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'FORBEARANCE', 'DELINQUENT', 'CLOSED')", name="check_loan_status"),
        Index("idx_loans_customer_due", "customer_id", "next_due_date", "status"),
    )

    def __repr__(self) -> str:
        return f"<Loan(id='{self.id}', customer_id='{self.customer_id}', emi={self.monthly_emi}, due={self.next_due_date})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    mcc_code: Mapped[Optional[str]] = mapped_column(String(4), ForeignKey("mcc_codes.code", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # CREDIT, DEBIT
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="transactions")
    mcc_ref: Mapped[Optional["MCCCode"]] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("type IN ('CREDIT', 'DEBIT')", name="check_transaction_type"),
        Index("idx_transactions_customer_time", "customer_id", "timestamp"),
        Index("idx_transactions_essential", "customer_id", "is_essential", "type", "timestamp"),
        Index("idx_transactions_mcc", "customer_id", "mcc_code"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id='{self.id}', mcc='{self.mcc_code}', amt={self.amount}, bal={self.balance_after})>"


class Intervention(Base):
    """
    Feature 3: Enhanced Interventions Table.
    Tracks daily interest accrual on deferred balances and repayment schedules.
    """
    __tablename__ = "interventions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    loan_id: Mapped[str] = mapped_column(String(36), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    projected_deficit: Mapped[float] = mapped_column(Float, nullable=False)
    survival_buffer: Mapped[float] = mapped_column(Float, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    original_emi: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_emi: Mapped[float] = mapped_column(Float, nullable=False)

    # Feature 3: Daily Financial Tracking & Accrual
    deferred_principal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    annual_interest_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    daily_accrual_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    days_deferred: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accrued_interest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    forbearance_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    forbearance_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    repayment_schedule_type: Mapped[str] = mapped_column(String(30), default="STREAMING_MICRO", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="PROPOSED", nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="interventions")
    loan: Mapped["Loan"] = relationship(back_populates="interventions")

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('STREAMING_MICRO_AMORTIZATION', 'INTEREST_ONLY_PAUSE', 'SPLIT_EMI', 'GRACE_PERIOD_EXTENSION')",
            name="check_action_type"
        ),
        CheckConstraint("status IN ('PROPOSED', 'ACCEPTED', 'ACTIVE', 'COMPLETED', 'REJECTED')", name="check_intervention_status"),
        CheckConstraint("repayment_schedule_type IN ('STREAMING_MICRO', 'BALLOON_AT_END', 'TENURE_EXTENSION')", name="check_repayment_schedule"),
        Index("idx_interventions_customer", "customer_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Intervention(id='{self.id}', action='{self.action_type}', accrued_interest={self.accrued_interest})>"
