from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from src.utils.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    currency = Column(String(3), nullable=True)
    amount = Column(BigInteger, nullable=True)
    customer_name = Column(String, nullable=True)
    date_of_transaction = Column(DateTime, nullable=True)
    sender_bank = Column(String, nullable=True)
    remark = Column(String, nullable=True)
    shop_name = Column(String, nullable=True)
    formatted_amount = Column(BigInteger, nullable=True)
