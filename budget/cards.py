from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .exceptions import DatabaseError, ValidationError
from .models import Card, Balance

class CardManager:
    """Manages payment cards in the budget"""

    def __init__(self, session: Session):
        self.session = session
        self.cards: List[str] = []

    def load_cards(self) -> List[str]:
        """Load cards from database and ensure default setup"""
        try:
            self.cards = [card.name for card in self.session.query(Card).order_by(Card.name).all()]

            # Ensure cash balance exists
            cash_balance = Balance(type="cash", amount=0.0)
            self.session.merge(cash_balance)

            if not self.cards:
                default_cards = ["Wise", "ICICI"]
                for card_name in default_cards:
                    new_card = Card(name=card_name)
                    self.session.add(new_card)
                    new_balance = Balance(type=card_name, amount=0.0)
                    self.session.merge(new_balance)
                self.session.commit()
                self.cards = default_cards
            else:
                for card_name in self.cards:
                    new_balance = Balance(type=card_name, amount=0.0)
                    self.session.merge(new_balance)
                self.session.commit()
            return self.cards
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to load cards: {e}")

    def add_new_card(self, name: str) -> bool:
        """Add a new payment card"""
        try:
            if not name or not name.strip():
                raise ValidationError("Card name cannot be empty")
            if name.strip() in self.cards:
                return False

            new_card = Card(name=name.strip())
            self.session.add(new_card)
            new_balance = Balance(type=name.strip(), amount=0.0)
            self.session.merge(new_balance)
            self.session.commit()
            self.cards.append(name.strip())
            return True
        except IntegrityError:
            self.session.rollback()
            return False
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to add card: {e}")