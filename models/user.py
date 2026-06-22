class User:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    def __str__(self):
        return f"User(lat={self.lat}, lon={self.lon})"

    def __repr__(self):
        return f"User(lat={self.lat}, lon={self.lon})"
