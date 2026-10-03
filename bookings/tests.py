from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from stations.models import Station, Charger, ChargingSlot
from bookings.models import Booking
from bookings.utils import expire_overdue_bookings, GRACE_PERIOD_MINUTES
from sessions_app.models import ChargingSession


class OverdueBookingExpirationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create driver user
        self.driver = User.objects.create_user(
            username='testdriver',
            password='password123',
            email='driver@example.com',
            role='DRIVER'
        )

        # Create admin user
        self.admin = User.objects.create_user(
            username='testadmin',
            password='password123',
            email='admin@example.com',
            role='ADMIN'
        )

        # Create station and charger
        self.station = Station.objects.create(
            station_code='ST100',
            name='Test Charging Hub',
            address='123 Test Expressway',
            latitude=12.9716,
            longitude=77.5946,
            status='Active'
        )

        self.charger = Charger.objects.create(
            station=self.station,
            charging_power_kW=50.0,
            connector_type='CCS2',
            status='Available'
        )

    def _create_slot_and_booking(self, minutes_offset_from_now):
        """
        Helper to create a slot and confirmed booking with start_time offset from now.
        minutes_offset_from_now can be negative for past times, e.g. -20 for 20 min ago.
        """
        target_dt = timezone.localtime() + timedelta(minutes=minutes_offset_from_now)
        slot_date = target_dt.date()
        slot_start_time = target_dt.time()
        slot_end_time = (target_dt + timedelta(hours=1)).time()

        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=slot_date,
            start_time=slot_start_time,
            end_time=slot_end_time,
            status='Reserved'
        )

        booking = Booking.objects.create(
            user=self.driver,
            station=self.station,
            charger=self.charger,
            slot=slot,
            booking_date=slot_date,
            booking_time=slot_start_time,
            status='Confirmed'
        )
        return slot, booking

    def test_booking_20_min_in_past_expires_on_visiting_stations_list(self):
        """
        Scenario 1: Slot start_time ~20 min in the past (> 15 min grace).
        Visiting /stations/ auto-cancels booking and reverts slot to Available.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-20)

        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('stations:driver_station_list'))
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Cancelled')
        self.assertEqual(slot.status, 'Available')

    def test_booking_20_min_in_past_expires_on_visiting_station_detail(self):
        """
        Scenario 1 (variant): Slot start_time ~20 min in past.
        Visiting /stations/<id>/ auto-cancels booking and frees the slot.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-20)

        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('stations:driver_station_detail', args=[self.station.id]))
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Cancelled')
        self.assertEqual(slot.status, 'Available')
        # The newly freed slot is now in available_slots
        self.assertIn(slot, response.context['available_slots'])

    def test_booking_20_min_in_past_expires_on_visiting_bookings_list(self):
        """
        Scenario 1 (variant): Slot start_time ~20 min in past.
        Visiting /bookings/ auto-cancels booking and frees the slot.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-20)

        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Cancelled')
        self.assertEqual(slot.status, 'Available')

    def test_booking_5_min_in_past_does_not_expire(self):
        """
        Scenario 2: Slot start_time ~5 min in the past (within 15-min grace period).
        Should NOT expire yet. Status remains Confirmed, slot remains Reserved.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-5)

        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Confirmed')
        self.assertEqual(slot.status, 'Reserved')

    def test_session_started_on_past_booking_prevents_expiration(self):
        """
        Scenario 3: Confirmed booking whose slot time has passed (~25 min in past),
        but a charging session was started (driver showed up).
        Booking should NOT auto-expire because has_session check protects it.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-25)

        # Create session on the booking
        session = ChargingSession.objects.create(
            booking=booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.localtime(),
            actual_load=48.0,
            charging_power_kW=50.0,
            energy_kWh=25.0,
            duration=0.5,
            traffic_density=1,
            weather_condition='Clear'
        )

        self.assertTrue(hasattr(booking, 'chargingsession'))

        # Run expiration check directly and via page visit
        self.client.login(username='testdriver', password='password123')
        response = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(response.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Confirmed')
        self.assertEqual(slot.status, 'Reserved')

    def test_ui_shows_cancelled_status_and_not_silently_stuck(self):
        """
        Scenario 4: Confirm booking status shows 'Cancelled' in the UI
        after expiration, rather than being stuck in Confirmed/Pending.
        Also check that Cancel action button is no longer shown for expired bookings.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-30)

        self.client.login(username='testdriver', password='password123')

        # Visit bookings list
        list_response = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Cancelled')

        # Visit booking detail page
        detail_response = self.client.get(reverse('bookings:booking_detail', args=[booking.id]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Cancelled')
        # The button to cancel booking should NOT be rendered when status is Cancelled
        self.assertNotContains(detail_response, 'Cancel Booking')
