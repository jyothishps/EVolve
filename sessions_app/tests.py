from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from stations.models import Station, Charger, ChargingSlot
from bookings.models import Booking
from sessions_app.models import ChargingSession
import datetime
from decimal import Decimal


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


class Step6BillingAndPaymentTests(TestCase):
    def setUp(self):
        self.client = Client()

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

        self.station = Station.objects.create(
            station_code='ST001',
            name='Central Station',
            address='123 Main St',
            latitude=12.9716,
            longitude=77.5946,
            location_type='City Center',
            number_of_chargers=1,
            price_per_kWh=Decimal('18.00'),
            status='Active'
        )

        self.charger = Charger.objects.create(
            station=self.station,
            charging_power_kW=50.0,
            connector_type='CCS2',
            status='Available'
        )

        self.slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=timezone.localdate(),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            status='Reserved'
        )

        self.booking = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=self.slot,
            booking_date=timezone.localdate(),
            booking_time=datetime.time(10, 0),
            status='Confirmed'
        )

    def test_1_edit_station_shows_price_per_kwh_and_can_change_it(self):
        """1. Edit a station: form shows Price per kWh and it can be changed."""
        self.client.login(username='admin_test', password='Password123!')
        edit_url = reverse('stations:station_edit', args=[self.station.id])
        get_resp = self.client.get(edit_url)
        self.assertEqual(get_resp.status_code, 200)
        content = get_resp.content.decode()
        self.assertIn('Price per kWh', content)
        self.assertIn('18.00', content)

        data = {
            'station_code': self.station.station_code,
            'name': self.station.name,
            'address': self.station.address,
            'latitude': self.station.latitude,
            'longitude': self.station.longitude,
            'location_type': self.station.location_type,
            'number_of_chargers': self.station.number_of_chargers,
            'status': self.station.status,
            'price_per_kWh': '22.50',
            'description': '',
        }
        post_resp = self.client.post(edit_url, data=data, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        self.station.refresh_from_db()
        self.assertEqual(self.station.price_per_kWh, Decimal('22.50'))

    def test_2_session_complete_generates_bill_message(self):
        """2. Complete session: message shows bill, e.g. 50 kWh x 18 = 900.00."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            traffic_density=0,
            weather_condition='Clear'
        )

        self.client.login(username='admin_test', password='Password123!')
        complete_url = reverse('sessions_app:session_complete', args=[session.id])
        resp = self.client.post(complete_url, follow=True)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('Session completed. Bill generated: Rs. 900.00. Collect payment at the station.', content)

        session.refresh_from_db()
        updated_booking = Booking.objects.get(id=self.booking.id)
        self.assertEqual(updated_booking.status, 'Completed')
        self.assertEqual(session.amount, Decimal('900.00'))
        self.assertEqual(session.price_per_kWh_applied, Decimal('18.00'))
        self.assertEqual(session.payment_status, 'Unpaid')

    def test_3_session_detail_billing_card_shows_details_and_red_unpaid_badge(self):
        """3. Session detail: Billing card shows energy, rate, total and red Unpaid badge."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='admin_test', password='Password123!')
        resp = self.client.get(reverse('sessions_app:session_detail', args=[session.id]))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        self.assertIn('50.0 kWh', content)
        self.assertIn('Rs. 18.00 per kWh', content)
        self.assertIn('Total: Rs. 900.00', content)
        self.assertIn('badge bg-danger', content)
        self.assertIn('Unpaid', content)

    def test_4_pick_method_and_mark_paid_turns_badge_green(self):
        """4. Pick method and click Mark as Paid -> badge turns green, shows method and time."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='admin_test', password='Password123!')
        mark_paid_url = reverse('sessions_app:session_mark_paid', args=[session.id])
        resp = self.client.post(mark_paid_url, data={'payment_method': 'UPI'}, follow=True)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('Payment of Rs. 900.00 recorded via UPI.', content)
        self.assertIn('badge bg-success', content)
        self.assertIn('Paid', content)
        self.assertIn('Method:</strong> UPI', content)
        self.assertIn('Paid at:', content)

        session.refresh_from_db()
        self.assertEqual(session.payment_status, 'Paid')
        self.assertEqual(session.payment_method, 'UPI')
        self.assertIsNotNone(session.paid_at)

    def test_5_mark_paid_again_refused(self):
        """5. Click Mark as Paid again: refused with 'already paid'."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Paid',
            payment_method='UPI',
            paid_at=timezone.now(),
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='admin_test', password='Password123!')
        mark_paid_url = reverse('sessions_app:session_mark_paid', args=[session.id])
        resp = self.client.post(mark_paid_url, data={'payment_method': 'Cash'}, follow=True)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('This session is already marked as paid.', content)

    def test_6_driver_booking_ticket_shows_bill_and_status(self):
        """6. Driver's booking ticket for completed booking shows bill and Paid/Unpaid badge."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='driver_test', password='Password123!')
        ticket_url = reverse('bookings:booking_detail', args=[self.booking.id])
        resp = self.client.get(ticket_url)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('Bill', content)
        self.assertIn('Energy: 50.0 kWh x Rs. 18.00', content)
        self.assertIn('Total: Rs. 900.00', content)
        self.assertIn('Unpaid - pay at the station', content)

        # Now mark as paid and check again
        session.mark_paid('Card')
        resp_paid = self.client.get(ticket_url)
        content_paid = resp_paid.content.decode()
        self.assertIn('Paid via Card', content_paid)

    def test_7_tariff_change_does_not_rewrite_old_bills(self):
        """7. Change station tariff afterwards: old session's bill stays the same."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.station.price_per_kWh = Decimal('30.00')
        self.station.save()

        session.refresh_from_db()
        self.assertEqual(session.amount, Decimal('900.00'))
        self.assertEqual(session.price_per_kWh_applied, Decimal('18.00'))

    def test_8_session_list_shows_amount_and_payment_columns(self):
        """8. Session list shows Amount and Payment columns."""
        ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Paid',
            payment_method='UPI',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='admin_test', password='Password123!')
        resp = self.client.get(reverse('sessions_app:session_list'))
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('<th>Amount</th>', content)
        self.assertIn('<th>Payment</th>', content)
        self.assertIn('Rs. 900.00', content)
        self.assertIn('badge bg-success', content)
        self.assertIn('Paid', content)

    def test_9_driver_account_denied_mark_paid(self):
        """9. Driver account hitting /sessions/1/mark-paid/ is denied."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.booking.status = 'Completed'
        self.booking.save()

        self.client.login(username='driver_test', password='Password123!')
        resp = self.client.post(reverse('sessions_app:session_mark_paid', args=[session.id]), data={'payment_method': 'Cash'}, follow=True)
        self.assertIn('Access denied. Admins only.', resp.content.decode())

    def test_10_mark_paid_refused_if_booking_not_completed(self):
        """10. Mark Paid on a session whose booking is not Completed is refused."""
        session = ChargingSession.objects.create(
            booking=self.booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0,
            price_per_kWh_applied=Decimal('18.00'),
            amount=Decimal('900.00'),
            payment_status='Unpaid',
            traffic_density=0,
            weather_condition='Clear'
        )
        self.assertEqual(self.booking.status, 'Confirmed')

        self.client.login(username='admin_test', password='Password123!')
        mark_paid_url = reverse('sessions_app:session_mark_paid', args=[session.id])
        resp = self.client.post(mark_paid_url, data={'payment_method': 'Cash'}, follow=True)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('Complete the session before recording payment.', content)
        session.refresh_from_db()
        self.assertEqual(session.payment_status, 'Unpaid')

