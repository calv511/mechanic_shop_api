from app import create_app
from app.models import db
import unittest


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.app = create_app("TestingConfig")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client = self.app.test_client()

        # Writing to inventory is mechanic-only, so every write test needs one
        self.client.post('/mechanics/', json={
            "name": "Jordan Reyes",
            "email": "jordan@email.com",
            "phone": "555-0200",
            "salary": 62000.0,
            "password": "123"
        })

    # ---------- helpers ----------

    def mechanic_auth_header(self, email="jordan@email.com", password="123"):
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

    def create_part(self, **overrides):
        payload = {"name": "Brake Pad Set", "price": 89.99}
        payload.update(overrides)
        return self.client.post('/inventory/', json=payload,
                                headers=self.mechanic_auth_header())

    # ---------- POST /inventory/ ----------

    def test_create_part(self):
        response = self.create_part()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "Brake Pad Set")
        self.assertEqual(response.json['price'], 89.99)

    def test_create_part_missing_field(self):
        response = self.client.post('/inventory/', json={"name": "Brake Pad Set"},
                                    headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['price'], ['Missing data for required field.'])

    def test_create_part_no_token(self):
        response = self.client.post('/inventory/', json={"name": "Brake Pad Set", "price": 89.99})
        self.assertEqual(response.status_code, 400)

    def test_create_part_with_customer_token(self):
        """Customers must not be able to edit the shop catalog."""
        response = self.client.post('/inventory/',
                                    json={"name": "Brake Pad Set", "price": 89.99},
                                    headers=self.customer_auth_header())
        self.assertEqual(response.status_code, 403)

    # ---------- GET /inventory/ ----------

    def test_get_parts(self):
        self.create_part()
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['name'], "Brake Pad Set")

    def test_get_parts_empty(self):
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    # ---------- GET /inventory/<id> ----------

    def test_get_single_part(self):
        part_id = self.create_part().json['id']
        response = self.client.get(f'/inventory/{part_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], "Brake Pad Set")

    def test_get_single_part_not_found(self):
        response = self.client.get('/inventory/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Part not found.")

    # ---------- PUT /inventory/<id> ----------

    def test_update_part(self):
        part_id = self.create_part().json['id']
        response = self.client.put(f'/inventory/{part_id}',
                                   json={"price": 104.50},
                                   headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['price'], 104.50)
        # Partial update: the name we did not send is untouched
        self.assertEqual(response.json['name'], "Brake Pad Set")

    def test_update_part_no_token(self):
        part_id = self.create_part().json['id']
        response = self.client.put(f'/inventory/{part_id}', json={"price": 104.50})
        self.assertEqual(response.status_code, 400)

    def test_update_part_with_customer_token(self):
        part_id = self.create_part().json['id']
        response = self.client.put(f'/inventory/{part_id}',
                                   json={"price": 104.50},
                                   headers=self.customer_auth_header())
        self.assertEqual(response.status_code, 403)

    def test_update_part_not_found(self):
        response = self.client.put('/inventory/999',
                                   json={"price": 104.50},
                                   headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 404)

    # ---------- DELETE /inventory/<id> ----------

    def test_delete_part(self):
        part_id = self.create_part().json['id']
        response = self.client.delete(f'/inventory/{part_id}',
                                      headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 200)
        # Confirm it is really gone rather than trusting the 200
        self.assertEqual(self.client.get(f'/inventory/{part_id}').status_code, 404)

    def test_delete_part_no_token(self):
        part_id = self.create_part().json['id']
        response = self.client.delete(f'/inventory/{part_id}')
        self.assertEqual(response.status_code, 400)

    def test_delete_part_with_customer_token(self):
        part_id = self.create_part().json['id']
        response = self.client.delete(f'/inventory/{part_id}',
                                      headers=self.customer_auth_header())
        self.assertEqual(response.status_code, 403)

    def test_delete_part_not_found(self):
        response = self.client.delete('/inventory/999',
                                      headers=self.mechanic_auth_header())
        self.assertEqual(response.status_code, 404)

    def test_delete_part_removes_it_from_tickets(self):
        """Inventory.ticket_parts cascades, so deleting a part strips it from
        every ticket it was recorded on."""
        part_id = self.create_part().json['id']
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

        added = self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}')
        self.assertEqual(len(added.json['parts']), 1)

        self.client.delete(f'/inventory/{part_id}', headers=self.mechanic_auth_header())

        # The ticket survives, but the part is no longer listed on it
        tickets = self.client.get('/service-tickets/')
        self.assertEqual(tickets.status_code, 200)
        self.assertEqual(len(tickets.json), 1)
        self.assertEqual(tickets.json[0]['parts'], [])


if __name__ == '__main__':
    unittest.main()
