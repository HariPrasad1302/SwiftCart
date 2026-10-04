import random

from locust import HttpUser, between, task


class Customer(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def list_stores(self):
        self.client.get("/v1/stores", name="/v1/stores")

    @task(3)
    def view_menu(self):
        sid = random.randint(1, 200)
        self.client.get(f"/v1/stores/{sid}/menu", name="/v1/stores/{id}/menu")