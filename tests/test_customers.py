from app import create_app
from app.models import db
import unittest


class TestCustomers(unittest.TestCase):
    def setUp(self):
        self.app = create_app("TestingConfig")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client = self.app.test_client()

    # ---------- helpers ----------
    # Shared setup lives here so each test says only what makes IT different.

    def create_customer(self, **overrides):
        """Create a customer. Pass overrides to change any field."""
        payload = {
            "name": "John Doe",
            "email": "jd@email.com",
            "phone": "555-555-5555",
            "password": "123"
        }
        payload.update(overrides)
        return self.client.post('/customers/', json=payload)

    def auth_header(self, email="jd@email.com", password="123"):
        """Log in and return the Authorization header the protected routes want."""
        response = self.client.post('/customers/login', json={
            "email": email,
            "password": password
        })
        token = response.json['token']
        return {'Authorization': f'Bearer {token}'}

    # ---------- POST /customers/ ----------

    def test_create_customer(self):
        response = self.create_customer()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "John Doe")
        # The password must never come back out of the API
        self.assertNotIn('password', response.json)

    def test_create_customer_missing_field(self):
        response = self.client.post('/customers/', json={
            "name": "John Doe",
            "phone": "555-555-5555",
            "password": "123"
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['email'], ['Missing data for required field.'])

    def test_create_customer_duplicate_email(self):
        self.create_customer()
        # Same email, different phone, so email is the only thing that can fail
        response = self.create_customer(phone="555-555-0000")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Email already associated with an account.")

    # ---------- POST /customers/login ----------

    def test_login(self):
        self.create_customer()
        response = self.client.post('/customers/login', json={
            "email": "jd@email.com",
            "password": "123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], "success")
        self.assertIn('token', response.json)

    def test_login_wrong_password(self):
        self.create_customer()
        response = self.client.post('/customers/login', json={
            "email": "jd@email.com",
            "password": "wrong"
        })
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('token', response.json)

    def test_login_missing_password(self):
        self.create_customer()
        response = self.client.post('/customers/login', json={"email": "jd@email.com"})
        self.assertEqual(response.status_code, 400)

    # ---------- GET /customers/ ----------

    def test_get_customers(self):
        self.create_customer()
        response = self.client.get('/customers/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['total_customers'], 1)
        self.assertEqual(response.json['customers'][0]['email'], "jd@email.com")

    def test_get_customers_pagination(self):
        # Three customers, one per page - unique email AND phone, both are unique columns
        for i in range(3):
            self.create_customer(email=f"c{i}@email.com", phone=f"555-000-000{i}")

        response = self.client.get('/customers/?page=2&per_page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['page'], 2)
        self.assertEqual(response.json['total_pages'], 3)
        self.assertEqual(len(response.json['customers']), 1)

    # ---------- GET /customers/<id> ----------

    def test_get_single_customer(self):
        customer_id = self.create_customer().json['id']
        response = self.client.get(f'/customers/{customer_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['email'], "jd@email.com")

    def test_get_single_customer_not_found(self):
        response = self.client.get('/customers/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Customer not found.")

    # ---------- GET /customers/my-tickets ----------

    def test_my_tickets(self):
        self.create_customer()
        response = self.client.get('/customers/my-tickets', headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        # A brand new customer has no tickets yet
        self.assertEqual(response.json, [])

    def test_my_tickets_no_token(self):
        self.create_customer()
        response = self.client.get('/customers/my-tickets')
        self.assertEqual(response.status_code, 400)

    # ---------- PUT /customers/ ----------

    def test_update_customer(self):
        self.create_customer()
        response = self.client.put('/customers/',
                                   json={"name": "Jane Doe"},
                                   headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], "Jane Doe")
        # A partial update must leave the fields we did not send alone
        self.assertEqual(response.json['email'], "jd@email.com")

    def test_update_customer_no_token(self):
        self.create_customer()
        response = self.client.put('/customers/', json={"name": "Jane Doe"})
        self.assertEqual(response.status_code, 400)

    def test_update_customer_invalid_token(self):
        self.create_customer()
        response = self.client.put('/customers/',
                                   json={"name": "Jane Doe"},
                                   headers={'Authorization': 'Bearer not-a-real-token'})
        self.assertEqual(response.status_code, 400)

    # ---------- DELETE /customers/ ----------

    def test_delete_customer(self):
        customer_id = self.create_customer().json['id']
        response = self.client.delete('/customers/', headers=self.auth_header())
        self.assertEqual(response.status_code, 200)
        # Confirm it is really gone, not just that the route said so
        self.assertEqual(self.client.get(f'/customers/{customer_id}').status_code, 404)

    def test_delete_customer_no_token(self):
        self.create_customer()
        response = self.client.delete('/customers/')
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
