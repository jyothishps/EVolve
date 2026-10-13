from django.test import TestCase
from django.urls import reverse
from .models import User


class AccountsAuthViewTests(TestCase):
    def setUp(self):
        self.driver_user = User.objects.create_user(
            username='rajesh_driver',
            email='rajesh@example.com',
            password='Password123!',
            role='DRIVER'
        )
        self.admin_user = User.objects.create_user(
            username='admin_boss',
            email='admin@example.com',
            password='AdminPassword123!',
            role='ADMIN'
        )

    def test_login_page_renders_enhanced_cockpit_elements(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Driver Sign In')
        self.assertContains(response, 'Sign In to Cockpit')
        self.assertContains(response, 'togglePasswordBtn')
        self.assertContains(response, 'Zero Queue Guarantee')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_login_invalid_credentials_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'rajesh_driver',
            'password': 'WrongPassword999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_login_driver_redirects_to_driver_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'rajesh_driver',
            'password': 'Password123!',
        })
        self.assertRedirects(response, reverse('accounts:driver_dashboard'))

    def test_login_admin_redirects_to_admin_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_boss',
            'password': 'AdminPassword123!',
        })
        self.assertRedirects(response, reverse('accounts:admin_dashboard'))

    def test_register_page_renders_enhanced_cockpit_elements(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Driver Account')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, 'pwdMeterFill')
        self.assertContains(response, 'Guaranteed Bay Reservation')

    def test_register_new_driver_success_creates_user_and_redirects(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'anita_ev',
            'email': 'anita@example.com',
            'password1': 'SecurePass987!',
            'password2': 'SecurePass987!',
        })
        self.assertRedirects(response, reverse('accounts:driver_dashboard'))
        created = User.objects.get(username='anita_ev')
        self.assertEqual(created.email, 'anita@example.com')
        self.assertEqual(created.role, 'DRIVER')
        self.assertTrue(created.is_driver())

    def test_register_authenticated_user_redirects_to_home(self):
        self.client.login(username='rajesh_driver', password='Password123!')
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('core:home'))

    def test_admin_dashboard_renders_metrics_and_command_matrix(self):
        self.client.login(username='admin_boss', password='AdminPassword123!')
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'Charging Hubs')
        self.assertContains(response, 'Charger Units')
        self.assertContains(response, 'Time Slots')
        self.assertContains(response, 'Energy Delivered')
        self.assertContains(response, 'Infrastructure & Management Hub')
        self.assertContains(response, 'Manage Stations')
        self.assertContains(response, 'Manage Chargers')

    def test_admin_dashboard_denies_driver_and_redirects(self):
        self.client.login(username='rajesh_driver', password='Password123!')
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertRedirects(response, reverse('accounts:driver_dashboard'))


