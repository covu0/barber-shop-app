"""
Database Models for Barber Shop Scheduling System
Author: Your Name
Date: 2024
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

# Create base class for all models
Base = declarative_base()

class Shop(Base):
    """Shop/Salon Information"""
    __tablename__ = 'shops'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    owner_name = Column(String(100))
    address = Column(String(200))
    phone = Column(String(20))
    email = Column(String(100))
    opening_time = Column(Time)  # e.g., 09:00
    closing_time = Column(Time)  # e.g., 20:00
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    employees = relationship("Employee", back_populates="shop", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="shop", cascade="all, delete-orphan")


class Employee(Base):
    """Barber/Stylist Information"""
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    specialization = Column(String(200))  # e.g., "Hair cutting, Beard styling"
    is_active = Column(Boolean, default=True)
    working_days = Column(String(50))  # e.g., "Mon,Tue,Wed,Thu,Fri"
    start_time = Column(Time)  # Daily start time
    end_time = Column(Time)    # Daily end time
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    shop = relationship("Shop", back_populates="employees")
    appointments = relationship("Appointment", back_populates="employee", cascade="all, delete-orphan")
    schedules = relationship("EmployeeSchedule", back_populates="employee", cascade="all, delete-orphan")


class Customer(Base):
    """Customer Information"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(100))
    preferred_barber_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    notes = Column(String(500))  # Special preferences or notes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan")
    preferred_barber = relationship("Employee", foreign_keys=[preferred_barber_id])


class Service(Base):
    """Services offered by the shop"""
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(200))
    duration_minutes = Column(Integer, default=30)
    price = Column(Float)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="service")


class Appointment(Base):
    """Appointment/Booking Information"""
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=True)
    
    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    status = Column(String(20), default='scheduled')  # scheduled, completed, cancelled, no-show
    notes = Column(String(500))
    price = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shop = relationship("Shop", back_populates="appointments")
    employee = relationship("Employee", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")


class EmployeeSchedule(Base):
    """Employee availability schedule (for handling special schedules)"""
    __tablename__ = 'employee_schedules'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    is_available = Column(Boolean, default=True)  # False for days off
    
    # Relationships
    employee = relationship("Employee", back_populates="schedules")


# Database setup function
def init_db(database_url="sqlite:///barber_shop.db"):
    """Initialize the database"""
    engine = create_engine(database_url, echo=True)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    # Create database tables
    engine = init_db()
    print("Database created successfully!")