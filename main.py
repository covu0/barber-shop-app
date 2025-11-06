"""
FastAPI Server for Barber Shop Scheduling System
RESTful API with endpoints for all operations
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date, time
from sqlalchemy.orm import Session

from models import init_db, get_session, Shop, Employee, Customer, Appointment, Service
from booking_manager import BookingManager
from ai_assistant import AIAssistant
import os
database_url = os.environ.get("DATABASE_URL", "sqlite:///barber_shop.db")
# Initialize FastAPI app
app = FastAPI(
    title="Barber Shop Scheduling API",
    description="AI-powered booking system for barber shops",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
engine = init_db()

# Dependency to get database session
def get_db():
    db = get_session(engine)
    try:
        yield db
    finally:
        db.close()


# Pydantic models for request/response
class ShopCreate(BaseModel):
    name: str
    owner_name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_time: str = "09:00"
    closing_time: str = "20:00"


class EmployeeCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    specialization: Optional[str] = None
    working_days: str = "Mon,Tue,Wed,Thu,Fri"
    start_time: str = "09:00"
    end_time: str = "18:00"


class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = 30
    price: float


class BookingCreate(BaseModel):
    employee_id: int
    customer_name: str
    customer_phone: str
    appointment_date: date
    start_time: str
    service_id: Optional[int] = None
    notes: Optional[str] = ""


class AIBookingRequest(BaseModel):
    message: str
    customer_phone: Optional[str] = None


class TimeSlot(BaseModel):
    start_time: time
    end_time: time
    available: bool


# API Endpoints

@app.get("/")
async def root():
    return {
        "message": "Barber Shop Scheduling API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "shops": "/api/shops",
            "employees": "/api/employees",
            "bookings": "/api/bookings",
            "ai_assistant": "/api/ai/chat"
        }
    }


# Shop Management Endpoints

@app.post("/api/shops", response_model=dict)
async def create_shop(shop: ShopCreate, db: Session = Depends(get_db)):
    """Create a new barber shop"""
    booking_manager = BookingManager(db)
    new_shop = booking_manager.create_shop(
        name=shop.name,
        owner_name=shop.owner_name,
        opening_time=shop.opening_time,
        closing_time=shop.closing_time,
        address=shop.address,
        phone=shop.phone,
        email=shop.email
    )
    return {
        "id": new_shop.id,
        "name": new_shop.name,
        "owner_name": new_shop.owner_name,
        "message": "Shop created successfully"
    }


@app.get("/api/shops")
async def get_shops(db: Session = Depends(get_db)):
    """Get all shops"""
    shops = db.query(Shop).all()
    return [{
        "id": s.id,
        "name": s.name,
        "owner_name": s.owner_name,
        "address": s.address,
        "phone": s.phone,
        "opening_time": s.opening_time.strftime("%H:%M"),
        "closing_time": s.closing_time.strftime("%H:%M")
    } for s in shops]


@app.get("/api/shops/{shop_id}")
async def get_shop(shop_id: int, db: Session = Depends(get_db)):
    """Get shop details"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    return {
        "id": shop.id,
        "name": shop.name,
        "owner_name": shop.owner_name,
        "address": shop.address,
        "phone": shop.phone,
        "opening_time": shop.opening_time.strftime("%H:%M"),
        "closing_time": shop.closing_time.strftime("%H:%M"),
        "employees": len(shop.employees),
        "active_appointments": len([a for a in shop.appointments if a.status == 'scheduled'])
    }


# Employee Management Endpoints

@app.post("/api/shops/{shop_id}/employees")
async def add_employee(shop_id: int, employee: EmployeeCreate, db: Session = Depends(get_db)):
    """Add employee to shop"""
    # Check if shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    booking_manager = BookingManager(db)
    new_employee = booking_manager.add_employee(
        shop_id=shop_id,
        name=employee.name,
        phone=employee.phone,
        email=employee.email,
        specialization=employee.specialization,
        working_days=employee.working_days,
        start_time=employee.start_time,
        end_time=employee.end_time
    )
    
    return {
        "id": new_employee.id,
        "name": new_employee.name,
        "message": "Employee added successfully"
    }


@app.get("/api/shops/{shop_id}/employees")
async def get_employees(shop_id: int, db: Session = Depends(get_db)):
    """Get all employees for a shop"""
    employees = db.query(Employee).filter(
        Employee.shop_id == shop_id,
        Employee.is_active == True
    ).all()
    
    return [{
        "id": e.id,
        "name": e.name,
        "phone": e.phone,
        "specialization": e.specialization,
        "working_days": e.working_days,
        "start_time": e.start_time.strftime("%H:%M"),
        "end_time": e.end_time.strftime("%H:%M")
    } for e in employees]


# Service Management Endpoints

@app.post("/api/shops/{shop_id}/services")
async def add_service(shop_id: int, service: ServiceCreate, db: Session = Depends(get_db)):
    """Add service to shop"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    booking_manager = BookingManager(db)
    new_service = booking_manager.add_service(
        shop_id=shop_id,
        name=service.name,
        description=service.description,
        duration_minutes=service.duration_minutes,
        price=service.price
    )
    
    return {
        "id": new_service.id,
        "name": new_service.name,
        "price": new_service.price,
        "message": "Service added successfully"
    }


@app.get("/api/shops/{shop_id}/services")
async def get_services(shop_id: int, db: Session = Depends(get_db)):
    """Get all services for a shop"""
    services = db.query(Service).filter(Service.shop_id == shop_id).all()
    
    return [{
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "duration_minutes": s.duration_minutes,
        "price": s.price
    } for s in services]


# Booking Endpoints

@app.post("/api/bookings")
async def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    """Create a new booking"""
    booking_manager = BookingManager(db)
    
    try:
        appointment = booking_manager.book_appointment(
            employee_id=booking.employee_id,
            customer_phone=booking.customer_phone,
            customer_name=booking.customer_name,
            appointment_date=booking.appointment_date,
            start_time=booking.start_time,
            service_id=booking.service_id,
            notes=booking.notes
        )
        
        return {
            "id": appointment.id,
            "appointment_date": appointment.appointment_date,
            "start_time": appointment.start_time.strftime("%H:%M"),
            "end_time": appointment.end_time.strftime("%H:%M"),
            "status": appointment.status,
            "message": "Booking created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/employees/{employee_id}/availability")
async def get_availability(
    employee_id: int,
    date: date,
    db: Session = Depends(get_db)
):
    """Get available time slots for an employee"""
    booking_manager = BookingManager(db)
    slots = booking_manager.get_employee_availability(employee_id, date)
    
    return slots


@app.get("/api/shops/{shop_id}/appointments")
async def get_shop_appointments(
    shop_id: int,
    date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get all appointments for a shop"""
    booking_manager = BookingManager(db)
    appointments = booking_manager.get_shop_appointments(shop_id, date)
    
    return [{
        "id": a.id,
        "employee_name": a.employee.name,
        "customer_name": a.customer.name,
        "date": a.appointment_date,
        "start_time": a.start_time.strftime("%H:%M"),
        "end_time": a.end_time.strftime("%H:%M"),
        "service": a.service.name if a.service else "Standard",
        "status": a.status
    } for a in appointments]


@app.delete("/api/bookings/{appointment_id}")
async def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """Cancel an appointment"""
    booking_manager = BookingManager(db)
    success = booking_manager.cancel_appointment(appointment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {"message": "Appointment cancelled successfully"}


# AI Assistant Endpoint

@app.post("/api/ai/chat")
async def ai_chat(request: AIBookingRequest, db: Session = Depends(get_db)):
    """Chat with AI assistant for booking"""
    booking_manager = BookingManager(db)
    ai_assistant = AIAssistant(booking_manager, use_openai=False)
    
    response = ai_assistant.process_request(
        request.message,
        request.customer_phone
    )
    
    return response


# Dashboard Endpoint

@app.get("/api/dashboard/{shop_id}")
async def get_dashboard(shop_id: int, db: Session = Depends(get_db)):
    """Get dashboard data for shop owner"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    today = date.today()
    
    # Today's appointments
    todays_appointments = db.query(Appointment).filter(
        Appointment.shop_id == shop_id,
        Appointment.appointment_date == today,
        Appointment.status == 'scheduled'
    ).count()
    
    # This week's appointments
    from datetime import timedelta
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_appointments = db.query(Appointment).filter(
        Appointment.shop_id == shop_id,
        Appointment.appointment_date >= week_start,
        Appointment.appointment_date <= week_end,
        Appointment.status == 'scheduled'
    ).count()
    
    # Active employees
    active_employees = db.query(Employee).filter(
        Employee.shop_id == shop_id,
        Employee.is_active == True
    ).count()
    
    # Total customers
    total_customers = db.query(Customer).join(Appointment).filter(
        Appointment.shop_id == shop_id
    ).distinct().count()
    
    return {
        "shop_name": shop.name,
        "today": today,
        "stats": {
            "todays_appointments": todays_appointments,
            "week_appointments": week_appointments,
            "active_employees": active_employees,
            "total_customers": total_customers
        },
        "opening_time": shop.opening_time.strftime("%H:%M"),
        "closing_time": shop.closing_time.strftime("%H:%M")
    }


# Health Check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    print("Starting Barber Shop Scheduling API...")
    print("Documentation available at: http://localhost:8000/docs")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)    
