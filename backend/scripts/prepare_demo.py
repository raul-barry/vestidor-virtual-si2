"""Populate the existing local demo customer through the current API."""
import httpx


def main():
    with httpx.Client(base_url="http://localhost:8000/api", timeout=30) as client:
        def call(method, path, body=None):
            response = client.request(method, path, json=body)
            response.raise_for_status()
            return response.json() if response.content else None

        auth = call("POST", "/auth/login", {"correo": "cliente@vestidor.local", "password": "Cliente123!"})
        client.headers["Authorization"] = "Bearer " + auth["access_token"]
        try:
            if not call("GET", "/orders"):
                products = call("GET", "/catalog/products")
                variants = call("GET", f"/catalog/products/{products[0]['id_producto']}/variants")
                call("POST", "/cart/items", {"id_variante": variants[0]["id_variante"], "cantidad": 1})
                order = call("POST", "/orders")
                payment = call("POST", "/payments", {"id_pedido": order["id_pedido"], "metodo_pago": "QR"})
                call("PUT", f"/payments/{payment['id_pago']}/approve")
            if not call("GET", "/reservations"):
                inventory = call("GET", "/reservations/availability")
                call("POST", "/reservations", {"id_inventario": inventory[0]["id_inventario"], "cantidad": 1})
            print("Demo ready: customer orders and reservations exist.")
        finally:
            call("POST", "/auth/logout")


if __name__ == "__main__":
    main()
