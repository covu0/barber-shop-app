"""
AI Assistant for Natural Language Booking
Uses OpenAI GPT or local LLM for understanding booking requests
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import re

# You can switch between OpenAI and a local solution
USE_OPENAI = False  # Set to True if you have OpenAI API key

if USE_OPENAI:
    from openai import OpenAI
else:
    # For learning purposes, we'll create a simple pattern-based assistant
    pass


@dataclass
class BookingIntent:
    """Represents a parsed booking intent"""
    action: str  # book, cancel, check_availability, list_services
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    employee_name: Optional[str] = None
    service_name: Optional[str] = None
    date: Optional[date] = None
    time: Optional[str] = None
    raw_text: str = ""


class AIAssistant:
    def __init__(self, booking_manager, use_openai=False, api_key=None):
        self.booking_manager = booking_manager
        self.use_openai = use_openai
        
        if use_openai and api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
        
        # Define patterns for pattern-based matching (fallback or primary method)
        self.patterns = {
            'book': [
                r'book.*appointment',
                r'schedule.*appointment',
                r'make.*appointment',
                r'i want.*appointment',
                r'can i.*book',
                r'i need.*haircut',
                r'reserve.*slot'
            ],
            'cancel': [
                r'cancel.*appointment',
                r'remove.*booking',
                r'delete.*appointment'
            ],
            'check': [
                r'available.*slots',
                r'free.*time',
                r'when.*available',
                r'check.*availability',
                r'what.*times'
            ],
            'list': [
                r'show.*appointments',
                r'list.*bookings',
                r'my.*appointments',
                r'upcoming.*appointments'
            ]
        }
        
        # Time patterns
        self.time_patterns = {
            'tomorrow': lambda: date.today() + timedelta(days=1),
            'today': lambda: date.today(),
            'next week': lambda: date.today() + timedelta(weeks=1),
            'this week': lambda: date.today(),
        }
    
    def parse_with_ai(self, text: str) -> BookingIntent:
        """Parse user intent using OpenAI GPT"""
        if not self.client:
            return self.parse_with_patterns(text)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a booking assistant for a barber shop. 
                     Extract booking information from user messages and return JSON with:
                     - action: (book/cancel/check_availability/list_services)
                     - customer_name: extracted name or null
                     - employee_name: barber name or null
                     - service_name: service requested or null
                     - date: in YYYY-MM-DD format or null
                     - time: in HH:MM format or null
                     """},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Convert to BookingIntent
            intent = BookingIntent(
                action=result.get('action', 'unknown'),
                customer_name=result.get('customer_name'),
                employee_name=result.get('employee_name'),
                service_name=result.get('service_name'),
                raw_text=text
            )
            
            # Parse date if provided
            if result.get('date'):
                intent.date = datetime.strptime(result['date'], '%Y-%m-%d').date()
            
            intent.time = result.get('time')
            
            return intent
            
        except Exception as e:
            print(f"AI parsing failed: {e}, falling back to patterns")
            return self.parse_with_patterns(text)
    
    def parse_with_patterns(self, text: str) -> BookingIntent:
        """Parse user intent using pattern matching (fallback method)"""
        text_lower = text.lower()
        
        # Determine action
        action = 'unknown'
        for act, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    action = act
                    break
            if action != 'unknown':
                break
        
        intent = BookingIntent(action=action, raw_text=text)
        
        # Extract customer name (simple heuristic)
        name_match = re.search(r'my name is (\w+ \w+)|i am (\w+ \w+)|this is (\w+ \w+)', text_lower)
        if name_match:
            intent.customer_name = name_match.group(1) or name_match.group(2) or name_match.group(3)
            intent.customer_name = intent.customer_name.title()
        
        # Extract employee preference
        with_match = re.search(r'with (\w+)', text_lower)
        if with_match:
            intent.employee_name = with_match.group(1).title()
        
        # Extract service
        if 'haircut' in text_lower:
            intent.service_name = 'Haircut'
        elif 'beard' in text_lower:
            intent.service_name = 'Haircut + Beard'
        elif 'color' in text_lower or 'coloring' in text_lower:
            intent.service_name = 'Hair Coloring'
        
        # Extract date
        for time_phrase, date_func in self.time_patterns.items():
            if time_phrase in text_lower:
                intent.date = date_func()
                break
        
        # Extract specific date (e.g., "January 15" or "15th")
        date_match = re.search(r'(\d{1,2})[st|nd|rd|th]?\s+(\w+)', text_lower)
        if date_match:
            try:
                day = int(date_match.group(1))
                month_str = date_match.group(2)
                current_year = date.today().year
                intent.date = datetime.strptime(f"{day} {month_str} {current_year}", "%d %B %Y").date()
            except:
                pass
        
        # Extract time
        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = time_match.group(2) or "00"
            am_pm = time_match.group(3)
            
            if am_pm and am_pm.lower() == 'pm' and hour < 12:
                hour += 12
            elif am_pm and am_pm.lower() == 'am' and hour == 12:
                hour = 0
            
            intent.time = f"{hour:02d}:{minute}"
        
        return intent
    
    def process_request(self, text: str, customer_phone: str = None) -> Dict:
        """Process a natural language booking request"""
        
        # Parse the request
        if self.use_openai:
            intent = self.parse_with_ai(text)
        else:
            intent = self.parse_with_patterns(text)
        
        # Handle based on action
        if intent.action == 'book':
            return self.handle_booking(intent, customer_phone)
        elif intent.action == 'cancel':
            return self.handle_cancellation(intent, customer_phone)
        elif intent.action == 'check':
            return self.handle_availability_check(intent)
        elif intent.action == 'list':
            return self.handle_list_appointments(intent, customer_phone)
        else:
            return {
                'success': False,
                'message': "I didn't understand your request. You can say things like:\n" +
                          "- 'Book an appointment for tomorrow at 2pm'\n" +
                          "- 'Check available slots with Mike'\n" +
                          "- 'Cancel my appointment'\n" +
                          "- 'Show my appointments'"
            }
    
    def handle_booking(self, intent: BookingIntent, customer_phone: str = None) -> Dict:
        """Handle booking request"""
        
        # Get shop (assuming single shop for now)
        from models import Shop, Employee, Service
        shop = self.booking_manager.session.query(Shop).first()
        if not shop:
            return {'success': False, 'message': 'No shop configured yet'}
        
        # Find employee
        employee = None
        if intent.employee_name:
            employee = self.booking_manager.session.query(Employee).filter(
                Employee.name.like(f'%{intent.employee_name}%')
            ).first()
        else:
            # Get any available employee
            employee = self.booking_manager.session.query(Employee).filter(
                Employee.shop_id == shop.id,
                Employee.is_active == True
            ).first()
        
        if not employee:
            return {'success': False, 'message': 'No available barber found'}
        
        # Find service
        service = None
        if intent.service_name:
            service = self.booking_manager.session.query(Service).filter(
                Service.name.like(f'%{intent.service_name}%')
            ).first()
        
        # Use default date/time if not provided
        booking_date = intent.date or date.today()
        booking_time = intent.time or "14:00"
        
        # Check if we have customer info
        if not intent.customer_name and not customer_phone:
            return {
                'success': False,
                'message': 'Please provide your name and phone number for the booking'
            }
        
        # Try to book
        try:
            appointment = self.booking_manager.book_appointment(
                employee_id=employee.id,
                customer_phone=customer_phone or "000-0000",
                customer_name=intent.customer_name or "Guest",
                appointment_date=booking_date,
                start_time=booking_time,
                service_id=service.id if service else None,
                notes=f"Booked via AI assistant: {intent.raw_text}"
            )
            
            return {
                'success': True,
                'message': f"Great! Your appointment is booked:\n" +
                          f"📅 Date: {booking_date.strftime('%A, %B %d, %Y')}\n" +
                          f"🕐 Time: {booking_time}\n" +
                          f"💈 Barber: {employee.name}\n" +
                          f"✂️ Service: {service.name if service else 'Standard Haircut'}\n" +
                          f"📞 Reference ID: {appointment.id}"
            }
        except ValueError as e:
            # Time slot not available, find next available
            next_slot = self.booking_manager.get_next_available_slot(employee_id=employee.id)
            if next_slot:
                return {
                    'success': False,
                    'message': f"That time slot is not available. The next available slot is:\n" +
                              f"📅 {next_slot['date'].strftime('%A, %B %d')}\n" +
                              f"🕐 {next_slot['time']}\n" +
                              f"Would you like to book this instead?"
                }
            else:
                return {
                    'success': False,
                    'message': "No available slots found in the next 30 days. Please try another barber or call the shop."
                }
    
    def handle_availability_check(self, intent: BookingIntent) -> Dict:
        """Check availability"""
        from models import Employee
        
        # If specific employee requested
        if intent.employee_name:
            employee = self.booking_manager.session.query(Employee).filter(
                Employee.name.like(f'%{intent.employee_name}%')
            ).first()
            
            if not employee:
                return {'success': False, 'message': f"No barber found with name '{intent.employee_name}'"}
            
            check_date = intent.date or date.today()
            slots = self.booking_manager.get_employee_availability(employee.id, check_date)
            
            if slots:
                available_times = [slot['start_time'].strftime('%H:%M') for slot in slots[:5]]
                return {
                    'success': True,
                    'message': f"Available slots with {employee.name} on {check_date.strftime('%A, %B %d')}:\n" +
                              f"⏰ {', '.join(available_times)}" +
                              (f"\n... and {len(slots)-5} more slots" if len(slots) > 5 else "")
                }
            else:
                return {
                    'success': False,
                    'message': f"{employee.name} has no available slots on {check_date.strftime('%A, %B %d')}"
                }
        else:
            # General availability
            shop = self.booking_manager.session.query(Shop).first()
            if not shop:
                return {'success': False, 'message': 'No shop configured'}
            
            next_slot = self.booking_manager.get_next_available_slot(shop_id=shop.id)
            if next_slot:
                return {
                    'success': True,
                    'message': f"Next available appointment:\n" +
                              f"💈 Barber: {next_slot.get('employee_name', 'Available')}\n" +
                              f"📅 Date: {next_slot['date'].strftime('%A, %B %d')}\n" +
                              f"🕐 Time: {next_slot['time'].strftime('%H:%M')}"
                }
            else:
                return {
                    'success': False,
                    'message': "No available slots found in the next 30 days"
                }
    
    def handle_cancellation(self, intent: BookingIntent, customer_phone: str = None) -> Dict:
        """Handle appointment cancellation"""
        # This would need appointment ID or customer lookup
        return {
            'success': False,
            'message': "To cancel an appointment, please provide your appointment ID or phone number"
        }
    
    def handle_list_appointments(self, intent: BookingIntent, customer_phone: str = None) -> Dict:
        """List customer's appointments"""
        if not customer_phone:
            return {
                'success': False,
                'message': "Please provide your phone number to view your appointments"
            }
        
        # Would implement customer appointment lookup here
        return {
            'success': True,
            'message': "Your upcoming appointments:\n[Implementation needed]"
        }


# Testing the AI Assistant
if __name__ == "__main__":
    from models import init_db, get_session
    from booking_manager import BookingManager
    
    # Initialize
    engine = init_db()
    session = get_session(engine)
    booking_manager = BookingManager(session)
    
    # Create AI Assistant
    ai_assistant = AIAssistant(booking_manager, use_openai=False)
    
    # Test various requests
    test_requests = [
        "I want to book an appointment for tomorrow at 2pm",
        "Can you check if Mike is available today?",
        "Book a haircut with Sarah next week",
        "What times are available this afternoon?",
        "I need a haircut and beard trim tomorrow morning",
        "Cancel my appointment",
    ]
    
    print("\n=== Testing AI Assistant ===\n")
    for request in test_requests:
        print(f"User: {request}")
        response = ai_assistant.process_request(request, customer_phone="555-1234")
        print(f"Assistant: {response['message']}\n")
        print("-" * 50 + "\n")