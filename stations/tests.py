from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import time, timedelta
from accounts.models import User
from stations.models import Station, Charger, ChargingSlot
from bookings.models import Booking
from sessions_app.models import ChargingSession


class Step6AdminActionsAndReopenTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@example.com',
            password='password123',
            role='ADMIN'
        )
        self.driver_user = User.objects.create_user(
            username='driver_test',
            email='driver@example.com',
            password='password123',
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
            status='Active'
        )
        self.charger = Charger.objects.create(
            station=self.station,
            charging_power_kW=50.0,
            connector_type='CCS2',
            status='Available'
        )

        self.future_date = timezone.localdate() + timedelta(days=2)
        self.past_date = timezone.localdate() - timedelta(days=2)

    def test_1_admin_booking_list_shows_cancel_and_cancels_booking(self):
        """1. Admin booking list: Confirmed booking shows Cancel button. Click -> Cancelled, slot Available."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Reserved'
        )
        booking = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot,
            booking_date=self.future_date,
            booking_time=time(10, 0),
            status='Confirmed'
        )

        self.client.login(username='admin_test', password='password123')
        resp = self.client.get(reverse('bookings:admin_booking_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        cancel_url = reverse('bookings:admin_booking_cancel', args=[booking.id])
        self.assertIn(cancel_url, content)
        self.assertIn('Cancel', content)
        self.assertIn(f"Cancel booking #{booking.id}? The slot will be freed.", content)

        # Admin cancels the booking via POST
        post_resp = self.client.post(cancel_url, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(booking.status, 'Cancelled')
        self.assertEqual(slot.status, 'Available')
        self.assertIn(f'Booking #{booking.id} cancelled. Slot is available again.', post_resp.content.decode())

    def test_2_cancel_button_hidden_for_cancelled_and_completed_bookings(self):
        """2. Cancel button hidden for Cancelled/Completed bookings."""
        slot_c = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(12, 0),
            end_time=time(13, 0),
            status='Available'
        )
        b_cancelled = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot_c,
            booking_date=self.future_date,
            booking_time=time(12, 0),
            status='Cancelled'
        )
        slot_comp = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status='Completed'
        )
        b_completed = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot_comp,
            booking_date=self.future_date,
            booking_time=time(14, 0),
            status='Completed'
        )

        self.client.login(username='admin_test', password='password123')
        resp = self.client.get(reverse('bookings:admin_booking_list'))
        content = resp.content.decode()

        self.assertNotIn(reverse('bookings:admin_booking_cancel', args=[b_cancelled.id]), content)
        self.assertNotIn(reverse('bookings:admin_booking_cancel', args=[b_completed.id]), content)

    def test_3_booking_with_session_cancel_refused(self):
        """3. Booking that already has a session: cancel refused with 'complete the session instead'."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Reserved'
        )
        booking = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot,
            booking_date=self.future_date,
            booking_time=time(10, 0),
            status='Confirmed'
        )
        ChargingSession.objects.create(
            booking=booking,
            station=self.station,
            charger=self.charger,
            timestamp=timezone.now(),
            actual_load=45.0,
            charging_power_kW=50.0,
            duration=1.0,
            energy_kWh=50.0
        )

        self.client.login(username='admin_test', password='password123')
        cancel_url = reverse('bookings:admin_booking_cancel', args=[booking.id])
        resp = self.client.post(cancel_url, follow=True)
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode()
        self.assertIn('already has a charging session. Complete the session instead of cancelling.', content)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Confirmed')

    def test_4_driver_bookings_page_shows_admin_cancelled_as_cancelled(self):
        """4. Driver's /bookings/ page shows the admin-cancelled booking as Cancelled."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Available'
        )
        booking = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot,
            booking_date=self.future_date,
            booking_time=time(10, 0),
            status='Cancelled'
        )

        self.client.login(username='driver_test', password='password123')
        resp = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        self.assertIn(f'<td>{booking.id}</td>', content)
        self.assertIn('Cancelled', content)

    def test_5_slot_list_completed_slot_shows_reopen_and_becomes_available(self):
        """5. Slot list: Completed slot shows Reopen. Click -> Available."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Completed'
        )

        self.client.login(username='admin_test', password='password123')
        resp = self.client.get(reverse('stations:slot_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        reopen_url = reverse('stations:slot_reopen', args=[slot.id])
        self.assertIn(reopen_url, content)
        self.assertIn('Reopen', content)

        post_resp = self.client.post(reopen_url, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        slot.refresh_from_db()
        self.assertEqual(slot.status, 'Available')
        self.assertIn('Slot reopened and available for booking.', post_resp.content.decode())

    def test_6_reopen_reserved_slot_button_hidden_and_manual_post_refused(self):
        """6. Reopen a Reserved slot: button not shown. Manual POST is refused."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Reserved'
        )

        self.client.login(username='admin_test', password='password123')
        resp = self.client.get(reverse('stations:slot_list'))
        content = resp.content.decode()

        reopen_url = reverse('stations:slot_reopen', args=[slot.id])
        self.assertNotIn(reopen_url, content)

        # Manual POST attempt
        post_resp = self.client.post(reopen_url, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        content_after = post_resp.content.decode()
        self.assertIn('Only Completed or Cancelled slots can be reopened.', content_after)

        slot.refresh_from_db()
        self.assertEqual(slot.status, 'Reserved')

    def test_7_reopen_past_slot_reopens_with_warning(self):
        """7. Reopen a slot whose date is past: slot reopens, with warning that drivers can't book it."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.past_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Completed'
        )

        self.client.login(username='admin_test', password='password123')
        reopen_url = reverse('stations:slot_reopen', args=[slot.id])
        post_resp = self.client.post(reopen_url, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        slot.refresh_from_db()
        self.assertEqual(slot.status, 'Available')
        self.assertIn('Slot reopened, but its date is in the past so drivers cannot book it.', post_resp.content.decode())

    def test_8_driver_can_book_reopened_future_slot_again(self):
        """8. Driver can book a reopened future slot again."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Completed'
        )

        # Admin reopens slot
        self.client.login(username='admin_test', password='password123')
        reopen_url = reverse('stations:slot_reopen', args=[slot.id])
        self.client.post(reopen_url)

        slot.refresh_from_db()
        self.assertEqual(slot.status, 'Available')

        # Driver logs in and books the slot
        self.client.login(username='driver_test', password='password123')
        book_resp = self.client.post(reverse('bookings:booking_create', args=[slot.id]), follow=True)
        self.assertEqual(book_resp.status_code, 200)

        slot.refresh_from_db()
        self.assertEqual(slot.status, 'Reserved')

        booking = Booking.objects.get(slot=slot, user=self.driver_user)
        self.assertEqual(booking.status, 'Confirmed')
        self.assertIn('Booking confirmed successfully.', book_resp.content.decode())

    def test_9_driver_denied_admin_cancel_and_reopen(self):
        """9. Driver visiting /bookings/manage/1/cancel/ or /stations/slots/1/reopen/ is denied."""
        slot = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Completed'
        )
        booking = Booking.objects.create(
            user=self.driver_user,
            station=self.station,
            charger=self.charger,
            slot=slot,
            booking_date=self.future_date,
            booking_time=time(10, 0),
            status='Confirmed'
        )

        self.client.login(username='driver_test', password='password123')

        # Cancel attempt by driver
        cancel_resp = self.client.post(reverse('bookings:admin_booking_cancel', args=[booking.id]), follow=True)
        self.assertIn('Access denied. Admins only.', cancel_resp.content.decode())

        # Reopen attempt by driver
        reopen_resp = self.client.post(reverse('stations:slot_reopen', args=[slot.id]), follow=True)
        self.assertIn('Access denied. Admins only.', reopen_resp.content.decode())
