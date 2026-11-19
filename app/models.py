#!/usr/bin/env python3
"""
SQLAlchemy models: Branch, User and Stock.
Product details are NOT stored: Stock only keeps the external product id.
"""
from datetime import datetime, timezone

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Integer,
                        String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"


def now():
    """
    Current time in UTC.
    """
    return datetime.now(timezone.utc)


class Branch(Base):
    """
    A store branch. It has staff users and stock lines.
    """
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now,
                                                 onupdate=now)

    users: Mapped[list["User"]] = relationship(back_populates="branch")
    stock: Mapped[list["Stock"]] = relationship(back_populates="branch")


class User(Base):
    """
    A user. Staff users belong to exactly one branch;
    the admin belongs to none and does not manage stock.
    Users are soft-deleted (deleted_at is set, the row stays).
    """
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN ('{ROLE_ADMIN}', '{ROLE_STAFF}')",
                        name="ck_users_role"),
        CheckConstraint(
            f"(role = '{ROLE_ADMIN}' AND branch_id IS NULL) OR "
            f"(role = '{ROLE_STAFF}' AND branch_id IS NOT NULL)",
            name="ck_users_branch_by_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default=ROLE_STAFF)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now,
                                                 onupdate=now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime,
                                                        nullable=True)

    branch: Mapped[Branch | None] = relationship(back_populates="users")

    @property
    def is_active(self):
        """
        A user is active while not soft-deleted.
        """
        return self.deleted_at is None

    def soft_delete(self):
        """
        Mark the user as deleted without removing the row.
        """
        self.deleted_at = now()


class Stock(Base):
    """
    Quantity of one external product in one branch.
    """
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("branch_id", "product_id",
                         name="uq_stock_branch_product"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    product_id: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now,
                                                 onupdate=now)

    branch: Mapped[Branch] = relationship(back_populates="stock")
