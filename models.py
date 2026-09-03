"""
SQLAlchemy 2.0 Declarative Models for Aegis
Relational Schema: Customers, Loans, Transactions, Interventions
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
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # CREDIT, DEBIT
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("type IN ('CREDIT', 'DEBIT')", name="check_transaction_type"),
        Index("idx_transactions_customer_time", "customer_id", "timestamp"),
        Index("idx_transactions_essential", "customer_id", "is_essential", "type", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id='{self.id}', type='{self.type}', amt={self.amount}, bal={self.balance_after})>"


class Intervention(Base):
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
        Index("idx_interventions_customer", "customer_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Intervention(id='{self.id}', action='{self.action_type}', status='{self.status}')>"
