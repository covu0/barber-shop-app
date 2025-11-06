"""
Booking Manager - Core Business Logic
Handles all appointment scheduling logic
"""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_
from models import Shop, Employee, Customer, Appointment, Service, EmployeeSchedule


class BookingManager:
    def __init__(self, session: Session):
        self.session = session
    
    def create_shop(self, name: str, owner_name: str, opening_time: str, closing_time: str, **kwargs) -> Shop:
        """Create a new shop"""
        shop = Shop(
            name=name,
            owner_name=owner_name,
            opening_time=datetime.strptime(opening_time, "%H:%M").time(),
            closing_time=datetime.strptime(closing_time, "%H:%M").time(),
            **kwargs
        )
        self.session.add(shop)
        self.session.commit()
        return shop
    
    def add_employee(self, shop_id: int, name: str, phone: str, 
                     working_days: str, start_time: str, end_time: str, **kwargs) -> Employee:
        """Add a new employee to a shop"""
        employee = Employee(
            shop_id=shop_id,
            name=name,
            phone=phone,
            working_days=working_days,
            start_time=datetime.strptime(start_time, "%H:%M").time(),
            end_time=datetime.strptime(end_time, "%H:%M").time(),
            **kwargs
        )
        self.session.add(employee)
        self.session.commit()
        return employee
    
    def add_service(self, shop_id: int, name: str, duration_minutes: int, price: float, **kwargs) -> Service:
        """Add a service to the shop"""
        service = Service(
            shop_id=shop_id,
            name=name,
            duration_minutes=duration_minutes,
            price=price,
            **kwargs
        )
        self.session.add(service)
        self.session.commit()
        return service
    
    def register_customer(self, name: str, phone: str, **kwargs) -> Customer:
        """Register a new customer or get existing one"""
        # Check if customer exists
        customer = self.session.query(Customer).filter_by(phone=phone).first()
        if customer:
            return customer
        
        # Create new customer
        customer = Customer(name=name, phone=phone, **kwargs)
        self.session.add(customer)
        self.session.commit()
        return customer
    
    def get_employee_availability(self, employee_id: int, date: date) -> List[Dict]:
        """Get available time slots for an employee on a specific date"""
        employee = self.session.query(Employee).get(employee_id)
        if not employee:
            return []
        
        # Check if employee works on this day
        day_name = date.strftime("%a")  # Get day abbreviation (Mon, Tue, etc.)
        if day_name not in employee.working_days.split(","):
            return []
        
        # Get employee's working hours
        start_time = employee.start_time
        end_time = employee.end_time
        
        # Get existing appointments for this employee on this date
        appointments = self.session.query(Appointment).filter(
            and_(
                Appointment.employee_id == employee_id,
                Appointment.appointment_date == date,
                Appointment.status != 'cancelled'
            )
        ).all()
        
        # Generate time slots (30-minute intervals by default)
        time_slots = []
        current_time = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)
        slot_duration = timedelta(minutes=30)
        
        while current_time + slot_duration <= end_datetime:
            slot_end = current_time + slot_duration
            
            # Check if slot is available (not booked)
            is_available = True
            for appointment in appointments:
                appt_start = datetime.combine(date, appointment.start_time)
                appt_end = datetime.combine(date, appointment.end_time)
                
                # Check for overlap
                if not (slot_end <= appt_start or current_time >= appt_end):
                    is_available = False
                    break
            
            if is_available:
                time_slots.append({
                    'start_time': current_time.time(),
                    'end_time': slot_end.time(),
                    'available': True
                })
            
            current_time = slot_end
        
        return time_slots
    
    def book_appointment(self, employee_id: int, customer_phone: str, customer_name: str,
                        appointment_date: date, start_time: str, service_id: Optional[int] = None,
                        notes: str = "") -> Appointment:
        """Book an appointment"""
        
        # Get or create customer
        customer = self.register_customer(customer_name, customer_phone)
        
        # Get employee and shop
        employee = self.session.query(Employee).get(employee_id)
        if not employee:
            raise ValueError("Employee not found")
        
        # Parse time
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        
        # Calculate end time based on service duration
        duration = 30  # Default 30 minutes
        if service_id:
            service = self.session.query(Service).get(service_id)
            if service:
                duration = service.duration_minutes
        
        end_time_obj = (datetime.combine(date.today(), start_time_obj) + 
                        timedelta(minutes=duration)).time()
        
        # Check availability
        conflicting = self.session.query(Appointment).filter(
            and_(
                Appointment.employee_id == employee_id,
                Appointment.appointment_date == appointment_date,
                Appointment.status != 'cancelled',
                or_(
                    and_(Appointment.start_time <= start_time_obj, 
                         Appointment.end_time > start_time_obj),
                    and_(Appointment.start_time < end_time_obj, 
                         Appointment.end_time >= end_time_obj)
                )
            )
        ).first()
        
        if conflicting:
            raise ValueError("Time slot not available")
        
        # Create appointment
        appointment = Appointment(
            shop_id=employee.shop_id,
            employee_id=employee_id,
            customer_id=customer.id,
            service_id=service_id,
            appointment_date=appointment_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            notes=notes,
            status='scheduled'
        )
        
        self.session.add(appointment)
        self.session.commit()
        return appointment
    
    def cancel_appointment(self, appointment_id: int) -> bool:
        """Cancel an appointment"""
        appointment = self.session.query(Appointment).get(appointment_id)
        if appointment:
            appointment.status = 'cancelled'
            self.session.commit()
            return True
        return False
    
    def get_shop_appointments(self, shop_id: int, date: Optional[date] = None) -> List[Appointment]:
        """Get all appointments for a shop"""
        query = self.session.query(Appointment).filter(
            Appointment.shop_id == shop_id,
            Appointment.status != 'cancelled'
        )
        
        if date:
            query = query.filter(Appointment.appointment_date == date)
        
        return query.order_by(Appointment.appointment_date, Appointment.start_time).all()
    
    def get_employee_appointments(self, employee_id: int, date: Optional[date] = None) -> List[Appointment]:
        """Get appointments for a specific employee"""
        query = self.session.query(Appointment).filter(
            Appointment.employee_id == employee_id,
            Appointment.status != 'cancelled'
        )
        
        if date:
            query = query.filter(Appointment.appointment_date == date)
        
        return query.order_by(Appointment.appointment_date, Appointment.start_time).all()
    
    def get_next_available_slot(self, employee_id: Optional[int] = None, 
                                shop_id: Optional[int] = None) -> Optional[Dict]:
        """Find the next available appointment slot"""
        # Start from today
        current_date = date.today()
        max_days_ahead = 30
        
        for days_ahead in range(max_days_ahead):
            check_date = current_date + timedelta(days=days_ahead)
            
            if employee_id:
                slots = self.get_employee_availability(employee_id, check_date)
                if slots:
                    return {
                        'employee_id': employee_id,
                        'date': check_date,
                        'time': slots[0]['start_time']
                    }
            elif shop_id:
                # Check all employees in the shop
                employees = self.session.query(Employee).filter(
                    Employee.shop_id == shop_id,
                    Employee.is_active == True
                ).all()
                
                for emp in employees:
                    slots = self.get_employee_availability(emp.id, check_date)
                    if slots:
                        return {
                            'employee_id': emp.id,
                            'employee_name': emp.name,
                            'date': check_date,
                            'time': slots[0]['start_time']
                        }
        
        return None


# Example usage and testing
if __name__ == "__main__":
    from models import init_db, get_session
    
    # Initialize database
    engine = init_db()
    session = get_session(engine)
    
    # Create booking manager
    booking_manager = BookingManager(session)
    
    # Create a shop
    shop = booking_manager.create_shop(
        name="Premium Cuts Barbershop",
        owner_name="John Doe",
        opening_time="09:00",
        closing_time="20:00",
        address="123 Main St",
        phone="555-0100"
    )
    print(f"Shop created: {shop.name}")
    
    # Add employees
    barber1 = booking_manager.add_employee(
        shop_id=shop.id,
        name="Mike Johnson",
        phone="555-0101",
        working_days="Mon,Tue,Wed,Thu,Fri,Sat",
        start_time="09:00",
        end_time="18:00",
        specialization="Classic cuts, Beard styling"
    )
    
    barber2 = booking_manager.add_employee(
        shop_id=shop.id,
        name="Sarah Williams",
        phone="555-0102",
        working_days="Tue,Wed,Thu,Fri,Sat",
        start_time="10:00",
        end_time="19:00",
        specialization="Modern styles, Hair coloring"
    )
    print(f"Employees added: {barber1.name}, {barber2.name}")
    
    # Add services
    service1 = booking_manager.add_service(
        shop_id=shop.id,
        name="Haircut",
        duration_minutes=30,
        price=25.00
    )
    
    service2 = booking_manager.add_service(
        shop_id=shop.id,
        name="Haircut + Beard",
        duration_minutes=45,
        price=35.00
    )
    print("Services added")