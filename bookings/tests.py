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

    def test_checkin_button_visible_and_successful_checkin(self):
        """
        1. Book a slot, go to booking detail -> "I've Arrived" button visible.
        2. Click it -> button disappears, replaced with "✓ Checked in at [timestamp]".
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=60)
        self.client.login(username='testdriver', password='password123')

        # Visit booking detail -> "I've Arrived - Check In" should be visible
        detail_resp = self.client.get(reverse('bookings:booking_detail', args=[booking.id]))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "I've Arrived - Check In")
        self.assertNotContains(detail_resp, "✓ Checked in at")

        # Submit check-in POST
        checkin_resp = self.client.post(
            reverse('bookings:booking_checkin', args=[booking.id]),
            follow=True
        )
        self.assertEqual(checkin_resp.status_code, 200)
        self.assertRedirects(checkin_resp, reverse('bookings:booking_detail', args=[booking.id]))

        booking.refresh_from_db()
        self.assertIsNotNone(booking.checked_in_at)

        # In response HTML: button disappeared, replaced with check-in timestamp
        self.assertNotContains(checkin_resp, "I've Arrived - Check In")
        self.assertContains(checkin_resp, "✓ Checked in at")

    def test_admin_booking_list_shows_checked_in_badge(self):
        """
        3. Admin booking list shows "Checked In" badge for checked-in bookings
        and "Not Yet" for unchecked bookings.
        """
        slot1, booking1 = self._create_slot_and_booking(minutes_offset_from_now=60)
        slot2, booking2 = self._create_slot_and_booking(minutes_offset_from_now=120)

        # Driver checks in for booking1 only
        booking1.check_in()

        # Admin visits admin booking list
        self.client.login(username='testadmin', password='password123')
        admin_resp = self.client.get(reverse('bookings:admin_booking_list'))
        self.assertEqual(admin_resp.status_code, 200)

        content = admin_resp.content.decode()
        self.assertIn('Checked In', content)
        self.assertIn('Not Yet', content)

    def test_checkin_protects_overdue_booking_from_autocancel(self):
        """
        4. Backdate slot's time to be overdue (20+ min past) with check-in recorded.
        Visiting /stations/ or /bookings/ should NOT auto-cancel (check-in protects it).
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=-25)
        booking.check_in()
        self.assertIsNotNone(booking.checked_in_at)

        self.client.login(username='testdriver', password='password123')

        # Visit /stations/
        stations_resp = self.client.get(reverse('stations:driver_station_list'))
        self.assertEqual(stations_resp.status_code, 200)

        # Visit /bookings/
        bookings_resp = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(bookings_resp.status_code, 200)

        booking.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(booking.status, 'Confirmed')
        self.assertEqual(slot.status, 'Reserved')

    def test_checkin_on_cancelled_or_completed_booking_rejected(self):
        """
        5. Try check in on an already-Cancelled or Completed booking -> rejected with message.
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=60)
        booking.status = 'Cancelled'
        booking.save()

        self.client.login(username='testdriver', password='password123')
        resp = self.client.post(
            reverse('bookings:booking_checkin', args=[booking.id]),
            follow=True
        )
        self.assertEqual(resp.status_code, 200)

        booking.refresh_from_db()
        self.assertIsNone(booking.checked_in_at)

        messages = list(resp.context['messages'])
        self.assertTrue(any('Check-in is only available for active bookings.' in str(m) for m in messages))

        # Test Completed status
        booking.status = 'Completed'
        booking.save()
        resp_completed = self.client.post(
            reverse('bookings:booking_checkin', args=[booking.id]),
            follow=True
        )
        self.assertEqual(resp_completed.status_code, 200)
        booking.refresh_from_db()
        self.assertIsNone(booking.checked_in_at)

    def test_checkin_twice_blocks_and_does_not_overwrite_timestamp(self):
        """
        6. Try check in twice on same booking -> second attempt shows 'already checked in'
        message, no duplicate timestamp overwrite (blocks with info message).
        """
        slot, booking = self._create_slot_and_booking(minutes_offset_from_now=60)
        self.client.login(username='testdriver', password='password123')

        # First check-in
        first_resp = self.client.post(
            reverse('bookings:booking_checkin', args=[booking.id]),
            follow=True
        )
        self.assertEqual(first_resp.status_code, 200)
        booking.refresh_from_db()
        original_checkin_time = booking.checked_in_at
        self.assertIsNotNone(original_checkin_time)

        # Second check-in attempt
        second_resp = self.client.post(
            reverse('bookings:booking_checkin', args=[booking.id]),
            follow=True
        )
        self.assertEqual(second_resp.status_code, 200)

        booking.refresh_from_db()
        # Verify timestamp was NOT modified or overwritten
        self.assertEqual(booking.checked_in_at, original_checkin_time)

        messages = list(second_resp.context['messages'])
        self.assertTrue(any('You have already checked in for this booking.' in str(m) for m in messages))


class OverlappingBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_date = timezone.localdate() + timedelta(days=1)
        self.different_date = timezone.localdate() + timedelta(days=2)

        # Drivers
        self.driver1 = User.objects.create_user(
            username='driver1', password='password123', email='d1@test.com', role='DRIVER'
        )
        self.driver2 = User.objects.create_user(
            username='driver2', password='password123', email='d2@test.com', role='DRIVER'
        )

        # Stations
        self.station1 = Station.objects.create(
            station_code='ST001', name='Station North', address='100 North Rd',
            latitude=12.97, longitude=77.59, status='Active'
        )
        self.station2 = Station.objects.create(
            station_code='ST002', name='Station South', address='200 South Rd',
            latitude=12.98, longitude=77.60, status='Active'
        )
        self.station3 = Station.objects.create(
            station_code='ST003', name='Station East', address='300 East Rd',
            latitude=12.99, longitude=77.61, status='Active'
        )
        self.station5 = Station.objects.create(
            station_code='ST005', name='Station West', address='500 West Rd',
            latitude=12.96, longitude=77.58, status='Active'
        )

        # Chargers
        self.charger1 = Charger.objects.create(
            station=self.station1, charging_power_kW=50.0, connector_type='CCS2', status='Available'
        )
        self.charger2 = Charger.objects.create(
            station=self.station2, charging_power_kW=50.0, connector_type='CCS2', status='Available'
        )
        self.charger3 = Charger.objects.create(
            station=self.station3, charging_power_kW=50.0, connector_type='CCS2', status='Available'
        )
        self.charger5 = Charger.objects.create(
            station=self.station5, charging_power_kW=50.0, connector_type='CCS2', status='Available'
        )

        from datetime import time
        # Slot A: ST001, 10:00-11:00 AM on test_date
        self.slot_a = ChargingSlot.objects.create(
            station=self.station1, charger=self.charger1, date=self.test_date,
            start_time=time(10, 0), end_time=time(11, 0), status='Available'
        )
        # Slot B: ST005, 10:30-11:30 AM on test_date (overlaps Slot A)
        self.slot_b = ChargingSlot.objects.create(
            station=self.station5, charger=self.charger5, date=self.test_date,
            start_time=time(10, 30), end_time=time(11, 30), status='Available'
        )
        # Slot C: ST002, 14:00-15:00 PM on test_date (same day, no overlap)
        self.slot_c = ChargingSlot.objects.create(
            station=self.station2, charger=self.charger2, date=self.test_date,
            start_time=time(14, 0), end_time=time(15, 0), status='Available'
        )
        # Slot D: ST003, 10:00-11:00 AM on different_date (different date)
        self.slot_d = ChargingSlot.objects.create(
            station=self.station3, charger=self.charger3, date=self.different_date,
            start_time=time(10, 0), end_time=time(11, 0), status='Available'
        )

    def test_book_slot_a_succeeds(self):
        """1. Book Slot A (ST001, 10:00-11:00 AM) as driver -> succeeds"""
        self.client.login(username='driver1', password='password123')
        resp = self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)
        self.assertEqual(resp.status_code, 200)

        self.slot_a.refresh_from_db()
        self.assertEqual(self.slot_a.status, 'Reserved')

        booking_a = Booking.objects.get(slot=self.slot_a, user=self.driver1)
        self.assertEqual(booking_a.status, 'Confirmed')

    def test_book_slot_b_overlapping_same_driver_blocked_with_error(self):
        """2. Try book Slot B (ST005, 10:30-11:30 AM, same day) as same driver -> blocked, error names clashing station/time"""
        self.client.login(username='driver1', password='password123')

        # First book Slot A
        self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)

        # Now attempt to book Slot B (overlaps 10:30 with 10:00-11:00)
        resp = self.client.post(reverse('bookings:booking_create', args=[self.slot_b.id]), follow=True)
        self.assertEqual(resp.status_code, 200)

        # Slot B should NOT be booked
        self.slot_b.refresh_from_db()
        self.assertEqual(self.slot_b.status, 'Available')
        self.assertFalse(Booking.objects.filter(slot=self.slot_b).exists())

        # Error message should name the clashing station and time
        messages = list(resp.context['messages'])
        self.assertTrue(any(
            'overlaps with your existing booking at Station North' in str(m) and '10:00:00 - 11:00:00' in str(m)
            for m in messages
        ))

    def test_book_slot_c_non_overlapping_same_day_succeeds(self):
        """3. Try book Slot C (ST002, 2:00-3:00 PM, same day) as same driver -> succeeds (no overlap)"""
        self.client.login(username='driver1', password='password123')

        # Book Slot A
        self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)

        # Book Slot C
        resp = self.client.post(reverse('bookings:booking_create', args=[self.slot_c.id]), follow=True)
        self.assertEqual(resp.status_code, 200)

        self.slot_c.refresh_from_db()
        self.assertEqual(self.slot_c.status, 'Reserved')
        self.assertTrue(Booking.objects.filter(slot=self.slot_c, user=self.driver1, status='Confirmed').exists())

    def test_book_slot_d_same_time_different_day_succeeds(self):
        """4. Try book Slot D (ST003, 10:00-11:00 AM, different day) as same driver -> succeeds (different date)"""
        self.client.login(username='driver1', password='password123')

        # Book Slot A
        self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)

        # Book Slot D
        resp = self.client.post(reverse('bookings:booking_create', args=[self.slot_d.id]), follow=True)
        self.assertEqual(resp.status_code, 200)

        self.slot_d.refresh_from_db()
        self.assertEqual(self.slot_d.status, 'Reserved')
        self.assertTrue(Booking.objects.filter(slot=self.slot_d, user=self.driver1, status='Confirmed').exists())

    def test_cancel_slot_a_retry_book_slot_b_succeeds(self):
        """5. Cancel Slot A, retry booking Slot B (10:30-11:30 AM) -> succeeds now (no active overlapping booking anymore)"""
        self.client.login(username='driver1', password='password123')

        # Book Slot A
        self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)
        booking_a = Booking.objects.get(slot=self.slot_a, user=self.driver1)

        # Cancel Slot A
        cancel_resp = self.client.post(reverse('bookings:booking_cancel', args=[booking_a.id]), follow=True)
        self.assertEqual(cancel_resp.status_code, 200)
        booking_a.refresh_from_db()
        self.assertEqual(booking_a.status, 'Cancelled')

        # Now booking Slot B should succeed
        resp_b = self.client.post(reverse('bookings:booking_create', args=[self.slot_b.id]), follow=True)
        self.assertEqual(resp_b.status_code, 200)

        self.slot_b.refresh_from_db()
        self.assertEqual(self.slot_b.status, 'Reserved')
        self.assertTrue(Booking.objects.filter(slot=self.slot_b, user=self.driver1, status='Confirmed').exists())

    def test_different_driver_books_slot_b_while_driver1_holds_slot_a(self):
        """6. Different driver books Slot B (10:30-11:30 AM) while first driver still holds Slot A at same time -> succeeds"""
        # Driver 1 books Slot A
        self.client.login(username='driver1', password='password123')
        self.client.post(reverse('bookings:booking_create', args=[self.slot_a.id]), follow=True)

        # Driver 2 logs in and books Slot B
        self.client.login(username='driver2', password='password123')
        resp_b = self.client.post(reverse('bookings:booking_create', args=[self.slot_b.id]), follow=True)
        self.assertEqual(resp_b.status_code, 200)

        self.slot_b.refresh_from_db()
        self.assertEqual(self.slot_b.status, 'Reserved')
        self.assertTrue(Booking.objects.filter(slot=self.slot_b, user=self.driver2, status='Confirmed').exists())


class BookingTicketCheckinAndAdminQueueTests(TestCase):
    """
    Tests covering Step 6 (Testing) and Step 7 (Expected Result):
    1. Book slot -> redirected to booking detail -> ticket layout, large Booking ID, QR code renders
    2. Check in -> 'I've Arrived' button disappears, checked-in confirmation shown
    3. Admin booking list -> checked-in booking appears in green 'Awaiting Session Start' box at top
    4. Start Session from that queue -> works, and booking disappears from checked-in queue after session starts
    5. Search box: valid booking ID -> list filters to just that row
    6. Search box: invalid/non-numeric -> empty result, no crash
    7. Clear search -> full list returns
    """

    def setUp(self):
        from datetime import time
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_user(
            username='test_admin',
            password='password123',
            email='admin@example.com',
            role='ADMIN'
        )

        # Drivers
        self.driver1 = User.objects.create_user(
            username='driver_alice',
            password='password123',
            email='alice@example.com',
            role='DRIVER'
        )
        self.driver2 = User.objects.create_user(
            username='driver_bob',
            password='password123',
            email='bob@example.com',
            role='DRIVER'
        )

        # Station and Charger
        self.station = Station.objects.create(
            station_code='ST200',
            name='Metro Fast Charging Hub',
            address='789 Downtown Boulevard',
            latitude=13.0827,
            longitude=80.2707,
            status='Active'
        )

        self.charger = Charger.objects.create(
            station=self.station,
            charging_power_kW=60.0,
            connector_type='CCS2',
            status='Available'
        )

        self.test_date = timezone.localdate() + timedelta(days=2)

        # Slots
        self.slot1 = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.test_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='Available'
        )

        self.slot2 = ChargingSlot.objects.create(
            station=self.station,
            charger=self.charger,
            date=self.test_date,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status='Available'
        )

    def test_book_slot_redirects_to_detail_with_ticket_layout_and_qr(self):
        """1. Book a slot -> redirected to booking detail -> shows ticket-style layout, large Booking ID, QR code renders"""
        self.client.login(username='driver_alice', password='password123')
        response = self.client.post(reverse('bookings:booking_create', args=[self.slot1.id]))

        booking = Booking.objects.get(slot=self.slot1, user=self.driver1)
        # Check redirection to booking detail
        self.assertRedirects(response, reverse('bookings:booking_detail', args=[booking.id]))

        # Follow redirect and inspect rendered HTML
        detail_resp = self.client.get(reverse('bookings:booking_detail', args=[booking.id]))
        self.assertEqual(detail_resp.status_code, 200)
        content = detail_resp.content.decode()

        # Ticket layout styling and large ID
        self.assertIn('ticket-card', content)
        self.assertIn('ticket-id', content)
        self.assertIn(f'#{booking.id}', content)

        # QR code container and QR script
        self.assertIn('id="qrcode"', content)
        self.assertIn('qrcode.min.js', content)
        self.assertIn(f'Booking #{booking.id} - {self.station.station_code}', content)

        # Details
        self.assertIn(self.station.name, content)
        self.assertIn(self.station.address, content)
        self.assertIn('60.0 kW', content)

        # Initial check-in button is present
        self.assertIn("I've Arrived - Check In", content)

    def test_check_in_hides_button_and_shows_confirmation(self):
        """2. Check in -> 'I've Arrived' button disappears, checked-in confirmation shown"""
        self.client.login(username='driver_alice', password='password123')
        # Create booking directly
        booking = Booking.objects.create(
            user=self.driver1,
            station=self.station,
            charger=self.charger,
            slot=self.slot1,
            booking_date=self.test_date,
            booking_time=self.slot1.start_time,
            status='Confirmed'
        )
        self.slot1.status = 'Reserved'
        self.slot1.save()

        # Before check-in: button is visible, confirmation text is not
        resp_before = self.client.get(reverse('bookings:booking_detail', args=[booking.id]))
        self.assertIn("I've Arrived - Check In", resp_before.content.decode())
        self.assertNotIn("Checked in at", resp_before.content.decode())

        # Perform check-in via POST with follow=True to follow redirect to booking_detail
        checkin_resp = self.client.post(reverse('bookings:booking_checkin', args=[booking.id]), follow=True)
        self.assertEqual(checkin_resp.status_code, 200)

        # Verify DB state
        booking.refresh_from_db()
        self.assertIsNotNone(booking.checked_in_at)

        # After check-in: button disappears, confirmation shown, success message displayed
        content_after = checkin_resp.content.decode()
        self.assertNotIn("I've Arrived - Check In", content_after)
        self.assertIn("Checked in at", content_after)
        self.assertIn("Checked in successfully", content_after)

    def test_admin_booking_list_checked_in_queue_and_start_session(self):
        """
        3 & 4. Admin booking list -> checked-in booking appears in green 'Awaiting Session Start' box at top.
        Click 'Start Session' from that queue -> works.
        After session starts, that booking disappears from the checked-in queue.
        """
        # Create booking and check in
        booking = Booking.objects.create(
            user=self.driver1,
            station=self.station,
            charger=self.charger,
            slot=self.slot1,
            booking_date=self.test_date,
            booking_time=self.slot1.start_time,
            status='Confirmed'
        )
        booking.check_in()

        # Admin logs in
        self.client.login(username='test_admin', password='password123')
        resp = self.client.get(reverse('bookings:admin_booking_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        # Green "Awaiting Session Start" box is visible
        self.assertIn('Checked-In - Awaiting Session Start (1)', content)
        self.assertIn(f'#{booking.id}', content)
        self.assertIn(self.driver1.username, content)
        self.assertIn(self.station.station_code, content)

        # "Start Session" button is in the queue linking to session start
        start_session_url = reverse('sessions_app:session_start', args=[booking.id])
        self.assertIn(f'href="{start_session_url}"', content)

        # Now start the charging session for this booking
        session_data = {
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'actual_load': 58.0,
            'charging_power_kW': 60.0,
            'duration': 1.0,
            'traffic_density': 1,
            'weather_condition': 'Clear',
        }
        post_resp = self.client.post(start_session_url, data=session_data, follow=True)
        self.assertEqual(post_resp.status_code, 200)

        # Verify session now exists
        self.assertTrue(ChargingSession.objects.filter(booking=booking).exists())

        # Admin visits booking list again: booking must DISAPPEAR from checked-in queue
        resp_after = self.client.get(reverse('bookings:admin_booking_list'))
        content_after = resp_after.content.decode()
        self.assertNotIn('Checked-In - Awaiting Session Start', content_after)

    def test_search_box_valid_id_filters_to_just_that_row(self):
        """5. Search box: type a valid booking ID -> list filters to just that row"""
        b1 = Booking.objects.create(
            user=self.driver1,
            station=self.station,
            charger=self.charger,
            slot=self.slot1,
            booking_date=self.test_date,
            booking_time=self.slot1.start_time,
            status='Confirmed'
        )
        b2 = Booking.objects.create(
            user=self.driver2,
            station=self.station,
            charger=self.charger,
            slot=self.slot2,
            booking_date=self.test_date,
            booking_time=self.slot2.start_time,
            status='Confirmed'
        )

        self.client.login(username='test_admin', password='password123')
        resp = self.client.get(reverse('bookings:admin_booking_list') + f'?search={b1.id}')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()

        # Row for b1 is present
        self.assertIn(f'#{b1.id}', content)
        self.assertIn(self.driver1.username, content)

        # Row for b2 is NOT present
        self.assertNotIn(f'#{b2.id}', content)
        self.assertNotIn(self.driver2.username, content)

        # Search box retains value and Clear button is visible
        self.assertIn(f'value="{b1.id}"', content)
        self.assertIn('Clear', content)

    def test_search_box_invalid_or_non_numeric_returns_empty_without_crash(self):
        """6. Search box: type invalid/non-numeric -> empty result, no crash"""
        Booking.objects.create(
            user=self.driver1,
            station=self.station,
            charger=self.charger,
            slot=self.slot1,
            booking_date=self.test_date,
            booking_time=self.slot1.start_time,
            status='Confirmed'
        )

        self.client.login(username='test_admin', password='password123')

        # Non-numeric text
        resp_str = self.client.get(reverse('bookings:admin_booking_list') + '?search=invalid_text')
        self.assertEqual(resp_str.status_code, 200)
        self.assertIn('No bookings found.', resp_str.content.decode())

        # Negative number
        resp_neg = self.client.get(reverse('bookings:admin_booking_list') + '?search=-5')
        self.assertEqual(resp_neg.status_code, 200)
        self.assertIn('No bookings found.', resp_neg.content.decode())

        # Non-existent numeric ID
        resp_missing = self.client.get(reverse('bookings:admin_booking_list') + '?search=999999')
        self.assertEqual(resp_missing.status_code, 200)
        self.assertIn('No bookings found.', resp_missing.content.decode())

    def test_clear_search_returns_full_list(self):
        """7. Clear search -> full list returns"""
        b1 = Booking.objects.create(
            user=self.driver1,
            station=self.station,
            charger=self.charger,
            slot=self.slot1,
            booking_date=self.test_date,
            booking_time=self.slot1.start_time,
            status='Confirmed'
        )
        b2 = Booking.objects.create(
            user=self.driver2,
            station=self.station,
            charger=self.charger,
            slot=self.slot2,
            booking_date=self.test_date,
            booking_time=self.slot2.start_time,
            status='Confirmed'
        )

        self.client.login(username='test_admin', password='password123')

        # First search for b1
        resp_searched = self.client.get(reverse('bookings:admin_booking_list') + f'?search={b1.id}')
        content_searched = resp_searched.content.decode()
        self.assertIn(f'#{b1.id}', content_searched)
        self.assertNotIn(f'#{b2.id}', content_searched)
        self.assertIn('Clear', content_searched)

        # Clear search by navigating back to admin_booking_list
        resp_cleared = self.client.get(reverse('bookings:admin_booking_list'))
        content_cleared = resp_cleared.content.decode()
        self.assertIn(f'#{b1.id}', content_cleared)
        self.assertIn(f'#{b2.id}', content_cleared)



