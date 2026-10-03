from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from stations.models import Station, Charger, ChargingSlot
from bookings.models import Booking
from sessions_app.models import ChargingSession
import datetime


class ChargingSessionStep6Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Admin and Driver users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='Password123!',
            email='admin@test.com',
            role='ADMIN'
        )
        self.driver_user = User.objects.create_user(
            username='driver_test',
            password='Password123!',
            email='driver@test.com',
            role='DRIVER'
        )

        # Create Station, Charger, and Slots
        self.station = Station.objects.create(
            station_code='ST001',
            name='Central Station',
            address='123 Main St',
            latitude=12.9716,
            longitude=77.5946,
            location_type='City Center',
            number_of_chargers=1,
            status='Active'
        )

        self.charger = Charger.objects.create(
            station=self.station,
            charging_power_kW=50.0,
            connector_type='CCS2',
            status='Available'
        )

        test_date = timezone.localdate() + datetime.timedelta(days=1)
        self.slot_confirmed = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=test_date,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            status='Reserved'
        )
        self.slot_pending = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=test_date,
            start_time=datetime.time(11, 0),
            end_time=datetime.time(12, 0),
            status='Available'
        )
        self.slot_cancelled = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=test_date,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(13, 0),
            status='Available'
        )

        # Create Bookings
        self.booking_confirmed = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=self.slot_confirmed,
            booking_date=test_date,
            booking_time=datetime.time(10, 0),
            status='Confirmed'
        )

        self.booking_pending = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=self.slot_pending,
            booking_date=test_date,
            booking_time=datetime.time(11, 0),
            status='Pending'
        )

        self.booking_cancelled = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=self.slot_cancelled,
            booking_date=test_date,
            booking_time=datetime.time(12, 0),
            status='Cancelled'
        )


        # Log in as admin
        self.client.force_login(self.admin_user)

    def test_1_admin_booking_list_shows_start_session_only_for_confirmed(self):
        """1. Admin booking list shows 'Start Session' only for Confirmed bookings"""
        response = self.client.get(reverse('bookings:admin_booking_list'))
        self.assertEqual(response.status_code, 200)

        confirmed_start_url = reverse('sessions_app:session_start', args=[self.booking_confirmed.id])
        pending_start_url = reverse('sessions_app:session_start', args=[self.booking_pending.id])
        cancelled_start_url = reverse('sessions_app:session_start', args=[self.booking_cancelled.id])

        content = response.content.decode()
        self.assertIn(confirmed_start_url, content)
        self.assertIn('Start Session', content)
        self.assertNotIn(pending_start_url, content)
        self.assertNotIn(cancelled_start_url, content)

    def test_2_start_session_form_shows_estimated_data_disclaimer(self):
        """2. Start session form shows estimated-data disclaimer"""
        response = self.client.get(reverse('sessions_app:session_start', args=[self.booking_confirmed.id]))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertIn('This project has no IoT hardware', content)
        self.assertIn('estimated/simulated', content)

    def test_3_submit_session_auto_calculates_energy_kwh(self):
        """3. Submit session -> energy_kWh auto-calculated (power x duration)"""
        data = {
            'timestamp': '2026-10-02 10:00:00',
            'actual_load': 40.0,
            'charging_power_kW': 50.0,
            'duration': 2.5,
            'traffic_density': 1,
            'weather_condition': 'Clear',
        }
        response = self.client.post(
            reverse('sessions_app:session_start', args=[self.booking_confirmed.id]),
            data=data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        session = ChargingSession.objects.get(booking=self.booking_confirmed)
        expected_energy = 50.0 * 2.5
        self.assertEqual(session.energy_kWh, expected_energy)
        self.assertEqual(session.energy_kWh, 125.0)

    def test_4_session_detail_shows_all_fields_correctly(self):
        """4. Session detail shows all fields correctly"""
        session = ChargingSession.objects.create(
            booking=self.booking_confirmed,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=42.5,
            charging_power_kW=60.0,
            duration=1.5,
            energy_kWh=90.0,
            traffic_density=2,
            weather_condition='Cloudy'
        )
        response = self.client.get(reverse('sessions_app:session_detail', args=[session.id]))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertIn(str(session.id), content)
        self.assertIn(self.booking_confirmed.user.username, content)
        self.assertIn(self.station.name, content)
        self.assertIn(self.station.station_code, content)
        self.assertIn(str(self.charger.id), content)
        self.assertIn('42.5', content)  # actual_load
        self.assertIn('60.0', content)  # charging_power_kW
        self.assertIn('1.5', content)   # duration
        self.assertIn('90.0', content)  # energy_kWh
        self.assertIn('High', content)  # traffic_density choice display (2 = High)
        self.assertIn('Cloudy', content) # weather_condition
        self.assertIn(self.booking_confirmed.status, content)

    def test_5_mark_complete_updates_booking_and_slot_status(self):
        """5. Mark Complete -> booking status Completed, slot status Completed (check via /stations/manage/slots/)"""
        session = ChargingSession.objects.create(
            booking=self.booking_confirmed,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=40.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            traffic_density=0,
            weather_condition='Clear'
        )

        self.assertEqual(self.booking_confirmed.status, 'Confirmed')
        self.assertEqual(self.slot_confirmed.status, 'Reserved')

        response = self.client.post(
            reverse('sessions_app:session_complete', args=[session.id]),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.booking_confirmed.refresh_from_db()
        self.slot_confirmed.refresh_from_db()

        self.assertEqual(self.booking_confirmed.status, 'Completed')
        self.assertEqual(self.slot_confirmed.status, 'Completed')

        # Check via /stations/manage/slots/ and /stations/slots/
        manage_slots_resp = self.client.get('/stations/manage/slots/')
        self.assertEqual(manage_slots_resp.status_code, 200)
        content = manage_slots_resp.content.decode()
        self.assertIn('Completed', content)
        self.assertIn(f'<td>{self.slot_confirmed.id}</td>', content)

    def test_6_try_start_second_session_on_same_booking_blocked(self):
        """6. Try start second session on same booking -> blocked with 'already exists' message"""
        # Create first session
        session = ChargingSession.objects.create(
            booking=self.booking_confirmed,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=35.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            traffic_density=0,
            weather_condition='Clear'
        )

        response = self.client.get(
            reverse('sessions_app:session_start', args=[self.booking_confirmed.id]),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Redirected to session_detail
        self.assertRedirects(response, reverse('sessions_app:session_detail', args=[session.id]))
        messages = list(response.context['messages'])
        self.assertTrue(any('already exists' in str(m) for m in messages))

        # Check no second session was created
        self.assertEqual(ChargingSession.objects.filter(booking=self.booking_confirmed).count(), 1)

    def test_7_try_start_session_on_non_confirmed_booking_blocked(self):
        """7. Try start session on non-Confirmed booking (Pending/Cancelled) -> blocked"""
        # Test Pending
        response_pending = self.client.get(
            reverse('sessions_app:session_start', args=[self.booking_pending.id]),
            follow=True
        )
        self.assertRedirects(response_pending, reverse('bookings:admin_booking_list'))
        messages_pending = list(response_pending.context['messages'])
        self.assertTrue(any('Only Confirmed bookings can start a session.' in str(m) for m in messages_pending))

        # Test Cancelled
        response_cancelled = self.client.get(
            reverse('sessions_app:session_start', args=[self.booking_cancelled.id]),
            follow=True
        )
        self.assertRedirects(response_cancelled, reverse('bookings:admin_booking_list'))
        messages_cancelled = list(response_cancelled.context['messages'])
        self.assertTrue(any('Only Confirmed bookings can start a session.' in str(m) for m in messages_cancelled))

        # Verify no sessions were created
        self.assertEqual(ChargingSession.objects.filter(booking=self.booking_pending).count(), 0)
        self.assertEqual(ChargingSession.objects.filter(booking=self.booking_cancelled).count(), 0)
