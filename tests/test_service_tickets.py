from app import create_app
from app.models import db
import unittest


class TestServiceTickets(unittest.TestCase):
    def setUp(self):
        self.app = create_app("TestingConfig")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client = self.app.test_client()

        # Every ticket needs an owner, so make one customer up front
        self.customer_id = self.client.post('/customers/', json={
            "name": "John Doe",
            "email": "jd@email.com",
            "phone": "555-555-5555",
            "password": "123"
        }).json['id']

    # ---------- helpers ----------

    def create_ticket(self, **overrides):
        """Open a service ticket for the customer created in setUp."""
        payload = {
            "VIN": "1HGCM82633A004352",
            "service_date": "2025-03-14",
            "service_desc": "Replaced front brake pads",
            "customer_id": self.customer_id
        }
        payload.update(overrides)
        return self.client.post('/service-tickets/', json=payload)

    def create_mechanic(self, **overrides):
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
        response = self.client.post('/mechanics/login', json={
            "email": email,
            "password": password
        })
        return {'Authorization': f"Bearer {response.json['token']}"}

    def create_part(self, **overrides):
        """Creating a part is mechanic-only, so make sure a mechanic exists first."""
        if not self.client.get('/mechanics/').json:
            self.create_mechanic()
        payload = {"name": "Brake Pad Set", "price": 89.99}
        payload.update(overrides)
        return self.client.post('/inventory/', json=payload,
                                headers=self.mechanic_auth_header())

    # ---------- POST /service-tickets/ ----------

    def test_create_ticket(self):
        response = self.create_ticket()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['VIN'], "1HGCM82633A004352")
        self.assertEqual(response.json['customer_id'], self.customer_id)
        # A new ticket starts with nothing attached to it
        self.assertEqual(response.json['mechanics'], [])
        self.assertEqual(response.json['parts'], [])

    def test_create_ticket_missing_field(self):
        response = self.client.post('/service-tickets/', json={
            "service_date": "2025-03-14",
            "service_desc": "Replaced front brake pads",
            "customer_id": self.customer_id
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['VIN'], ['Missing data for required field.'])

    def test_create_ticket_unknown_customer(self):
        response = self.create_ticket(customer_id=999)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Customer not found.")

    # ---------- GET /service-tickets/ ----------

    def test_get_tickets(self):
        self.create_ticket()
        response = self.client.get('/service-tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['service_desc'], "Replaced front brake pads")

    def test_get_tickets_empty(self):
        response = self.client.get('/service-tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    # ---------- PUT /<id>/assign-mechanic/<id> ----------

    def test_assign_mechanic(self):
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']

        response = self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['mechanics']), 1)
        self.assertEqual(response.json['mechanics'][0]['id'], mechanic_id)

    def test_assign_mechanic_twice(self):
        """This route is strict: assigning an already-assigned mechanic is an error."""
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']
        self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{mechanic_id}')

        response = self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'],
                         "Mechanic already assigned to this service ticket.")

    def test_assign_mechanic_ticket_not_found(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.put(f'/service-tickets/999/assign-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Service ticket not found.")

    def test_assign_mechanic_mechanic_not_found(self):
        ticket_id = self.create_ticket().json['id']
        response = self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Mechanic not found.")

    # ---------- PUT /<id>/remove-mechanic/<id> ----------

    def test_remove_mechanic(self):
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']
        self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{mechanic_id}')

        response = self.client.put(f'/service-tickets/{ticket_id}/remove-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mechanics'], [])

    def test_remove_mechanic_not_assigned(self):
        """Also strict: removing a mechanic who was never assigned is an error."""
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']

        response = self.client.put(f'/service-tickets/{ticket_id}/remove-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'],
                         "Mechanic is not assigned to this service ticket.")

    def test_remove_mechanic_ticket_not_found(self):
        mechanic_id = self.create_mechanic().json['id']
        response = self.client.put(f'/service-tickets/999/remove-mechanic/{mechanic_id}')
        self.assertEqual(response.status_code, 404)

    # ---------- PUT /<id>/edit ----------

    def test_edit_add_and_remove(self):
        ticket_id = self.create_ticket().json['id']
        first_id = self.create_mechanic().json['id']
        second_id = self.create_mechanic(email="second@email.com").json['id']
        self.client.put(f'/service-tickets/{ticket_id}/assign-mechanic/{first_id}')

        # Swap one mechanic for the other in a single request
        response = self.client.put(f'/service-tickets/{ticket_id}/edit', json={
            "add_ids": [second_id],
            "remove_ids": [first_id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual([m['id'] for m in response.json['mechanics']], [second_id])

    def test_edit_ignores_unknown_ids(self):
        """Unlike assign-mechanic, /edit skips bad IDs silently instead of erroring."""
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']

        response = self.client.put(f'/service-tickets/{ticket_id}/edit', json={
            "add_ids": [mechanic_id, 999],
            "remove_ids": [888]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['mechanics']), 1)

    def test_edit_same_id_added_and_removed(self):
        """Adds are applied before removes, so an ID in both lists ends up removed."""
        ticket_id = self.create_ticket().json['id']
        mechanic_id = self.create_mechanic().json['id']

        response = self.client.put(f'/service-tickets/{ticket_id}/edit', json={
            "add_ids": [mechanic_id],
            "remove_ids": [mechanic_id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mechanics'], [])

    def test_edit_empty_body(self):
        """Both lists default to empty, so {} is valid and changes nothing."""
        ticket_id = self.create_ticket().json['id']
        response = self.client.put(f'/service-tickets/{ticket_id}/edit', json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['mechanics'], [])

    def test_edit_ticket_not_found(self):
        response = self.client.put('/service-tickets/999/edit', json={"add_ids": []})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Service ticket not found.")

    # ---------- POST /<id>/add-part/<id> ----------

    def test_add_part(self):
        ticket_id = self.create_ticket().json['id']
        part_id = self.create_part().json['id']

        response = self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}',
                                    json={"quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['parts']), 1)
        self.assertEqual(response.json['parts'][0]['quantity'], 2)
        self.assertEqual(response.json['parts'][0]['part']['name'], "Brake Pad Set")

    def test_add_part_defaults_to_one(self):
        """The body is optional - with no body at all the quantity should be 1."""
        ticket_id = self.create_ticket().json['id']
        part_id = self.create_part().json['id']

        response = self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['parts'][0]['quantity'], 1)

    def test_add_part_twice_accumulates(self):
        """A part can only appear once per ticket, so a repeat adds to the quantity."""
        ticket_id = self.create_ticket().json['id']
        part_id = self.create_part().json['id']

        self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}',
                         json={"quantity": 2})
        response = self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}',
                                    json={"quantity": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['parts']), 1)
        self.assertEqual(response.json['parts'][0]['quantity'], 5)

    def test_add_part_invalid_quantity(self):
        ticket_id = self.create_ticket().json['id']
        part_id = self.create_part().json['id']

        response = self.client.post(f'/service-tickets/{ticket_id}/add-part/{part_id}',
                                    json={"quantity": 0})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "quantity must be a positive integer.")

    def test_add_part_ticket_not_found(self):
        part_id = self.create_part().json['id']
        response = self.client.post(f'/service-tickets/999/add-part/{part_id}')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Service ticket not found.")

    def test_add_part_part_not_found(self):
        ticket_id = self.create_ticket().json['id']
        response = self.client.post(f'/service-tickets/{ticket_id}/add-part/999')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['error'], "Part not found.")


if __name__ == '__main__':
    unittest.main()
