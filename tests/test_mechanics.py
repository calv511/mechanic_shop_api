from app import create_app
from app.models import db
import unittest


class TestMechanics(unittest.TestCase):
    def setUp(self):
        self.app = create_app("TestingConfig")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client = self.app.test_client()

    # ---------- helpers ----------

    def create_mechanic(self, **overrides):
        """Create a mechanic. Pass overrides to change any field."""
        payload = {
            "name": "Jordan Reyes",
            "email": "jordan@email.com",
            "phone": "555-0200",
            "salary": 62000.0,
            "password": "123"
        }
        payload.update(overrides)
        return self.client.post('/mechanics/', json=payload)

    def mechanic_auth_header(self, email="jordan@email.com", password="123"):
        """Log in as a mechanic and return the Authorization header."""
        response = self.client.post('/mechanics/login', json={
            "email": email,
            "password": password
        })
        return {'Authorization': f"Bearer {response.json['token']}"}

    def customer_auth_header(self):
        """A valid token that is NOT a mechanic token - used to test the 403 path."""
        self.client.post('/customers/', json={
            "name": "John Doe",
            "email": "jd@email.com",
            "phone": "555-555-5555",
            "password": "123"
        })
        response = self.client.post('/customers/login', json={
            "email": "jd@email.com",
            "password": "123"
        })
        return {'Authorization': f"Bearer {response.json['token']}"}

    # ---------- POST /mechanics/ ----------

    def test_create_mechanic(self):
        response = self.create_mechanic()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "Jordan Reyes")
        self.assertNotIn('password', response.json)

    def test_create_mechanic_missing_field(self):
        response = self.client.post('/mechanics/', json={
            "name": "Jordan Reyes",
            "email": "jordan@email.com",
            "phone": "555-0200",
            "password": "123"
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['salary'], ['Missing data for required field.'])

    def test_create_mechanic_duplicate_email(self):
        self.create_mechanic()
        response = self.create_mechanic(name="Someone Else")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Email already associated with an account.")

    # ---------- POST /mechanics/login ----------

    def test_mechanic_login(self):
        self.create_mechanic()
        response = self.client.post('/mechanics/login', json={
            "email": "jordan@email.com",
            "password": "123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], "success")
        self.assertIn('token', response.json)

    def test_mechanic_login_wrong_password(self):
        self.create_mechanic()
        response = self.client.post('/mechanics/login', json={
            "email": "jordan@email.com",
            "password": "wrong"
        })
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('token', response.json)

    def test_mechanic_login_missing_password(self):
        self.create_mechanic()
        response = self.client.post('/mechanics/login', json={"email": "jordan@email.com"})
        self.assertEqual(response.status_code, 400)

    # ---------- GET /mechanics/ ----------

    def test_get_mechanics(self):
        self.create_mechanic()
        response = self.client.get('/mechanics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['email'], "jordan@email.com")

    def test_get_mechanics_empty(self):
        response = self.client.get('/mechanics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    # ---------- GET /mechanics/most-tickets ----------

    def test_most_tickets_ranking(self):
        busy_id = self.create_mechanic().json['id']
        idle_id = self.create_mechanic(email="idle@email.com").json['id']

        # A mechanic only ranks if there is a ticket to assign them to
        customer_id = self.client.post('/customers/', json={
            "name": "John Doe", "email": "jd@email.com",
            "phone": "555-555-5555", "password": "123"
        }).json['id']
        ticket_id = self.client.post('/service-tickets/', json={
            "VIN": "1HGCM82633A004352",
            "service_date": "2025-03-14",
            "service_desc": "Brake job",
            "customer_id": customer_id
        }).json['id']
        self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{busy_id}')

        response = self.client.get('/mechanics/most-tickets')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 2)
        # Busiest first, and mechanics with no tickets still appear with a 0
        self.assertEqual(response.json[0]['id'], busy_id)
        self.assertEqual(response.json[0]['ticket_count'], 1)
        self.assertEqual(response.json[1]['id'], idle_id)
        self.assertEqual(response.json[1]['ticket_count'], 0)

    # ---------- PUT /mechanics/<id> ----------

    def test_update_mechanic(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.put(f'/mechanics/{mechanic_id}',
                                   json={"salary": 70000.0},
                                   headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['salary'], 70000.0)
        # Partial update: the fields we did not send are untouched
        self.assertEqual(response.json['name'], "Jordan Reyes")

    def test_update_mechanic_no_token(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.put(f'/mechanics/{mechanic_id}', json={"salary": 70000.0})
        self.assertEqual(response.status_code, 400)

    def test_update_mechanic_with_customer_token(self):
        """A customer token decodes fine but lacks the mechanic role claim."""
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.put(f'/mechanics/{mechanic_id}',
                                   json={"salary": 70000.0},
                                   headers=self.customer_auth_header())
        self.assertEqual(response.status_code, 403)

    def test_update_mechanic_not_found(self):
        self.create_mechanic()
        response = self.client.put('/mechanics/999',
                                   json={"salary": 70000.0},
                                   headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 404)

    # ---------- DELETE /mechanics/<id> ----------

    def test_delete_mechanic(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.delete(f'/mechanics/{mechanic_id}',
                                      headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 200)
        # Confirm it is really gone rather than trusting the 200
        self.assertEqual(self.client.get('/mechanics/').json, [])

    def test_delete_mechanic_no_token(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.delete(f'/mechanics/{mechanic_id}')
        self.assertEqual(response.status_code, 400)

    def test_delete_mechanic_not_found(self):
        self.create_mechanic()
        response = self.client.delete('/mechanics/999',
                                      headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
