"""
Setup Script - Initialize Database with Sample Data
Run this after creating the database to add sample data for testing
"""

from models import init_db, get_session
from booking_manager import BookingManager
from datetime import date, timedelta

def setup_sample_data():
    print("🚀 Setting up sample barber shop data...")
    
    # Initialize database
    engine = init_db()
    session = get_session(engine)
    booking_manager = BookingManager(session)
    
    # Create a sample shop
    print("Creating shop...")
    shop = booking_manager.create_shop(
        name="Premium Cuts Barbershop",
        owner_name="John Doe",
        opening_time="09:00",
        closing_time="20:00",
        address="123 Main Street, Downtown",
        phone="555-0100",
        email="info@premiumcuts.com"
    )
    print(f"✅ Shop created: {shop.name} (ID: {shop.id})")
    
    # Add employees
    print("\nAdding employees...")
    employees = [
        {
            "name": "Mike Johnson",
            "phone": "555-0101",
            "specialization": "Classic cuts, Beard styling, Hot towel shaves",
            "working_days": "Mon,Tue,Wed,Thu,Fri,Sat",
            "start_time": "09:00",
            "end_time": "18:00"
        },
        {
            "name": "Sarah Williams",
            "phone": "555-0102",
            "specialization": "Modern styles, Hair coloring, Highlights",
            "working_days": "Tue,Wed,Thu,Fri,Sat",
            "start_time": "10:00",
            "end_time": "19:00"
        },
        {
            "name": "Carlos Martinez",
            "phone": "555-0103",
            "specialization": "Fades, Line-ups, Kids cuts",
            "working_days": "Mon,Wed,Thu,Fri,Sat,Sun",
            "start_time": "11:00",
            "end_time": "20:00"
        }
    ]
    
    for emp_data in employees:
        emp = booking_manager.add_employee(shop_id=shop.id, **emp_data)
        print(f"✅ Added employee: {emp.name}")
    
    # Add services
    print("\nAdding services...")
    services = [
        {"name": "Basic Haircut", "duration_minutes": 30, "price": 25.00, 
         "description": "Standard men's haircut"},
        {"name": "Haircut + Beard", "duration_minutes": 45, "price": 35.00,
         "description": "Haircut with beard trim and styling"},
        {"name": "Premium Package", "duration_minutes": 60, "price": 50.00,
         "description": "Haircut, beard, hot towel, and styling"},
        {"name": "Kids Cut", "duration_minutes": 20, "price": 15.00,
         "description": "Children's haircut (12 and under)"},
        {"name": "Beard Trim Only", "duration_minutes": 15, "price": 12.00,
         "description": "Beard trimming and shaping"},
        {"name": "Hair Color", "duration_minutes": 90, "price": 65.00,
         "description": "Full hair coloring service"}
    ]
    
    for service_data in services:
        service = booking_manager.add_service(shop_id=shop.id, **service_data)
        print(f"✅ Added service: {service.name} - ${service.price}")
    
    # Add sample bookings for today and tomorrow
    print("\nAdding sample bookings...")
    sample_bookings = [
        {
            "employee_id": 1,
            "customer_name": "Alex Thompson",
            "customer_phone": "555-2001",
            "appointment_date": date.today(),
            "start_time": "14:00",
            "service_id": 1,
            "notes": "Regular customer, likes it short on the sides"
        },
        {
            "employee_id": 2,
            "customer_name": "David Chen",
            "customer_phone": "555-2002",
            "appointment_date": date.today(),
            "start_time": "15:30",
            "service_id": 2,
            "notes": "First time customer"
        },
        {
            "employee_id": 1,
            "customer_name": "Robert Wilson",
            "customer_phone": "555-2003",
            "appointment_date": date.today() + timedelta(days=1),
            "start_time": "10:00",
            "service_id": 3,
            "notes": "Premium package for special event"
        },
        {
            "employee_id": 3,
            "customer_name": "Tommy Johnson (Kid)",
            "customer_phone": "555-2004",
            "appointment_date": date.today() + timedelta(days=1),
            "start_time": "11:30",
            "service_id": 4,
            "notes": "8 years old, parent will accompany"
        }
    ]
    
    for booking_data in sample_bookings:
        try:
            appointment = booking_manager.book_appointment(**booking_data)
            print(f"✅ Booked: {booking_data['customer_name']} on {booking_data['appointment_date']} at {booking_data['start_time']}")
        except Exception as e:
            print(f"❌ Failed to book for {booking_data['customer_name']}: {e}")
    
    print("\n" + "="*50)
    print("✨ Sample data setup complete!")
    print("="*50)
    print("\nYour shop is ready with:")
    print(f"  • 1 Shop: {shop.name}")
    print(f"  • 3 Employees")
    print(f"  • 6 Services")
    print(f"  • 4 Sample appointments")
    print("\n📝 Shop ID: 1 (use this for API calls)")
    print("\n🚀 You can now:")
    print("  1. Run 'python main.py' to start the API server")
    print("  2. Open 'frontend.html' in your browser")
    print("  3. Visit http://localhost:8000/docs for API documentation")
    
    return shop.id

if __name__ == "__main__":
    shop_id = setup_sample_data()