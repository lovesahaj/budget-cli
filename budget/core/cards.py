"""Payment card management module.

This module provides functionality for managing payment cards in the budget
tracker, including loading cards from the database, adding new cards, and
ensuring associated balance accounts are created.
"""

from typing import List

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budget.domain.exceptions import DatabaseError, ValidationError
from budget.domain.models import Balance, Card


class CardManager:
    """Manages payment cards and their associated balances.

    The CardManager handles all operations related to payment cards, including
    loading existing cards, adding new ones, and automatically creating balance
    accounts for each card.

    Attributes:
        session (Session): SQLAlchemy database session.
        cards (List[str]): List of card names currently loaded in memory.

    Example:
        >>> with BudgetManager() as bm:
        ...     card_manager = CardManager(bm.session)
        ...     cards = card_manager.load_cards()
        ...     card_manager.add_new_card("Mastercard")
    """

    def __init__(self, session: Session):
        """Initialize the CardManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        logger.debug("Initializing CardManager")
        self.session = session
        self.cards: List[str] = []

    def load_cards(self) -> List[str]:
        """Load cards from database and ensure default setup.

        Loads all payment cards from the database. If no cards exist, creates
        default cards ("Wise" and "ICICI"). Also ensures that balance accounts
        exist for cash and all cards.

        Returns:
            List[str]: List of card names sorted alphabetically.

        Raises:
            DatabaseError: If loading cards fails or balance creation fails.

        Example:
            >>> cards = card_manager.load_cards()
            >>> print(cards)  # ['ICICI', 'Wise']
        """
        logger.info("Loading cards from database")
        try:
            self.cards = [
                card.name for card in self.session.query(Card).order_by(Card.name).all()
            ]
            logger.debug(f"Found {len(self.cards)} existing cards: {self.cards}")

            # Ensure cash balance exists
            cash_balance = Balance(type="cash", amount=0.0)
            self.session.merge(cash_balance)
            logger.debug("Ensured cash balance exists")

            if not self.cards:
                logger.info("No cards found, creating default cards")
                default_cards = ["Wise", "ICICI"]
                for card_name in default_cards:
                    logger.debug(f"Creating default card: {card_name}")
                    new_card = Card(name=card_name)
                    self.session.add(new_card)
                    new_balance = Balance(type=card_name, amount=0.0)
                    self.session.merge(new_balance)
                self.session.flush()
                self.cards = default_cards
                logger.info(f"Created default cards: {default_cards}")
            else:
                logger.debug("Ensuring balance accounts exist for all cards")
                for card_name in self.cards:
                    new_balance = Balance(type=card_name, amount=0.0)
                    self.session.merge(new_balance)
                self.session.flush()
                logger.info(f"Successfully loaded {len(self.cards)} cards")
            return self.cards
        except Exception as e:
            logger.error(f"Failed to load cards: {e}")
            self.session.rollback()
            raise DatabaseError(f"Failed to load cards: {e}")

    def add_new_card(self, name: str) -> bool:
        """Add a new payment card to the database.

        Creates a new card and its associated balance account. The card name
        is trimmed of whitespace and checked for uniqueness.

        Args:
            name: Name of the card to add (will be trimmed of whitespace).

        Returns:
            bool: True if the card was added successfully, False if a card
                 with that name already exists.

        Raises:
            ValidationError: If the card name is empty or whitespace-only.
            DatabaseError: If the database operation fails.

        Example:
            >>> success = card_manager.add_new_card("Amex")
            >>> if success:
            ...     print("Card added successfully")
        """
        logger.info(f"Attempting to add new card: {name}")
        try:
            if not name or not name.strip():
                logger.warning("Attempted to add card with empty name")
                raise ValidationError("Card name cannot be empty")
            if name.strip() in self.cards:
                logger.warning(f"Card '{name.strip()}' already exists")
                return False

            logger.debug(f"Creating new card: {name.strip()}")
            new_card = Card(name=name.strip())
            self.session.add(new_card)
            new_balance = Balance(type=name.strip(), amount=0.0)
            self.session.merge(new_balance)
            self.session.flush()
            self.cards.append(name.strip())
            logger.success(f"Successfully added card: {name.strip()}")
            return True
        except IntegrityError as e:
            logger.error(f"Integrity error when adding card '{name}': {e}")
            self.session.rollback()
            return False
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to add card '{name}': {e}")
            self.session.rollback()
            raise DatabaseError(f"Failed to add card: {e}")
