#!/usr/bin/env python3
"""
Stock operations with their validation rules.
Every change of stock goes through these functions.
"""
from app.models import Branch, Stock
from app.product_api import product_exists


class StockError(ValueError):
    """
    Raised when a stock operation breaks a rule.
    """


def check_quantity(quantity):
    """
    A stock change must be a positive integer (bool is refused).
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise StockError("La quantité doit être un nombre entier.")
    if quantity <= 0:
        raise StockError("La quantité doit être supérieure à 0.")


def get_branch(session, branch_id):
    """
    Return the branch or raise StockError if it does not exist.
    """
    branch = session.get(Branch, branch_id)
    if branch is None:
        raise StockError(f"Le magasin {branch_id} n'existe pas.")
    return branch


def get_or_create_stock(session, branch_id, product_id):
    """
    Return the stock line of a product in a branch (created at 0).
    """
    stock = session.query(Stock).filter_by(
        branch_id=branch_id, product_id=product_id).first()
    if stock is None:
        stock = Stock(branch_id=branch_id, product_id=product_id,
                      quantity=0)
        session.add(stock)
    return stock


def add_stock(session, branch_id, product_id, quantity,
              check_product=product_exists):
    """
    Add quantity units of product_id to the branch stock.
    """
    check_quantity(quantity)
    get_branch(session, branch_id)
    product_id = str(product_id)
    if not check_product(product_id):
        raise StockError(f"Le produit {product_id} n'existe pas.")
    stock = get_or_create_stock(session, branch_id, product_id)
    stock.quantity += quantity
    session.commit()
    return stock


def remove_stock(session, branch_id, product_id, quantity):
    """
    Remove quantity units; the stock can never become negative.
    """
    check_quantity(quantity)
    get_branch(session, branch_id)
    stock = session.query(Stock).filter_by(
        branch_id=branch_id, product_id=str(product_id)).first()
    available = stock.quantity if stock else 0
    if quantity > available:
        raise StockError(f"Stock insuffisant : {available} disponible(s), "
                         f"{quantity} demandé(s).")
    stock.quantity -= quantity
    session.commit()
    return stock
