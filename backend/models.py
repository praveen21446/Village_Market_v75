from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from .database import Base
class User(Base):
    __tablename__='users'; id=Column(Integer,primary_key=True); phone=Column(String(30),unique=True,index=True,nullable=False); email=Column(String(180),nullable=True); name=Column(String(100),nullable=False); role=Column(String(20),nullable=False); verified=Column(Boolean,default=True); created_at=Column(DateTime,default=datetime.utcnow)

class AdminAccount(Base):
    __tablename__='admin_accounts'; id=Column(Integer,primary_key=True); admin_id=Column(String(80),unique=True,index=True,nullable=False); display_name=Column(String(100),nullable=False); password_hash=Column(String(255),nullable=False); user_id=Column(Integer,ForeignKey('users.id'),unique=True,nullable=False); created_by_user_id=Column(Integer,ForeignKey('users.id'),nullable=True); active=Column(Boolean,default=True,nullable=False); created_at=Column(DateTime,default=datetime.utcnow)

class OtpCode(Base):
    __tablename__='otp_codes'; id=Column(Integer,primary_key=True); phone=Column(String(30),index=True,nullable=False); code=Column(String(6),nullable=False); expires_at=Column(DateTime,nullable=False)
class Session(Base):
    __tablename__='sessions'; token=Column(String(64),primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=False); role=Column(String(20),nullable=True); expires_at=Column(DateTime,nullable=False)
class Crop(Base):
    __tablename__='crops'; id=Column(Integer,primary_key=True); farmer_id=Column(Integer,ForeignKey('users.id'),nullable=False); name=Column(String(100),nullable=False); category=Column(String(40),nullable=False); quantity_kg=Column(Float,nullable=False); available_kg=Column(Float,nullable=False); location=Column(String(240),nullable=False); address_line=Column(String(240)); village=Column(String(100)); mandal=Column(String(100)); district=Column(String(100)); state=Column(String(100)); pincode=Column(String(10)); landmark=Column(String(180)); latitude=Column(String(30)); longitude=Column(String(30)); expected_price=Column(Float,nullable=False); quality=Column(String(50),nullable=False); harvest_date=Column(String(20),nullable=False); details=Column(Text,default=''); photo=Column(String(255)); photos_json=Column(Text,default='[]'); status=Column(String(20),default='pending'); market_price=Column(Float); admin_note=Column(Text,default=''); low_stock_threshold=Column(Float,default=10); created_at=Column(DateTime,default=datetime.utcnow)
class Booking(Base):
    __tablename__='bookings'; id=Column(Integer,primary_key=True); crop_id=Column(Integer,ForeignKey('crops.id'),nullable=False); buyer_id=Column(Integer,ForeignKey('users.id'),nullable=False); quantity_kg=Column(Float,nullable=False); amount=Column(Float,nullable=False,default=0); final_price=Column(Float); farmer_note=Column(Text); status=Column(String(25),default='requested'); payment_status=Column(String(20),default='unpaid'); delivery_method=Column(String(20),default='delivery'); delivery_address=Column(Text); delivery_latitude=Column(String(30)); delivery_longitude=Column(String(30)); payment_reference=Column(String(120)); delivery_otp=Column(String(6)); delivered_at=Column(DateTime); created_at=Column(DateTime,default=datetime.utcnow); updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class Review(Base):
    __tablename__='reviews'; id=Column(Integer,primary_key=True); booking_id=Column(Integer,ForeignKey('bookings.id'),unique=True,nullable=False); buyer_id=Column(Integer,ForeignKey('users.id'),nullable=False); crop_id=Column(Integer,ForeignKey('crops.id'),nullable=False); rating=Column(Integer,nullable=False); comment=Column(Text,default=''); created_at=Column(DateTime,default=datetime.utcnow)
class Notification(Base):
    __tablename__='notifications'; id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=False); title=Column(String(150),nullable=False); message=Column(Text,nullable=False); read=Column(Boolean,default=False); created_at=Column(DateTime,default=datetime.utcnow)

class SavedAddress(Base):
    __tablename__='saved_addresses'; id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True); kind=Column(String(20),nullable=False,index=True); label=Column(String(100),default='Saved address'); data_json=Column(Text,nullable=False); created_at=Column(DateTime,default=datetime.utcnow)

class SupportTicket(Base):
    __tablename__='support_tickets'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    subject=Column(String(120),nullable=False)
    category=Column(String(40),nullable=False,default='general')
    status=Column(String(20),nullable=False,default='open',index=True)
    created_at=Column(DateTime,default=datetime.utcnow)
    updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

class SupportMessage(Base):
    __tablename__='support_messages'
    id=Column(Integer,primary_key=True)
    ticket_id=Column(Integer,ForeignKey('support_tickets.id'),nullable=False,index=True)
    sender_user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    sender_role=Column(String(20),nullable=False)
    message=Column(Text,nullable=False)
    created_at=Column(DateTime,default=datetime.utcnow)

