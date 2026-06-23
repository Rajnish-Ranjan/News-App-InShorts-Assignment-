import requests


class Location:
    def __init__(self, lat, lon, radius, bounding_box=None):
        self.lat = lat
        self.lon = lon
        self.radius = radius
        self.bounding_box = bounding_box

    @classmethod
    def from_name(cls, location_name: str) -> "Location | None":
        """
        Use location name to create location object
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": location_name, "format": "json", "limit": 1}
        headers = {"User-Agent": "InShortsApp/1.0"}
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data:
                print("Location data:", data[0])
                bounding_box = data[0].get("boundingbox", None)
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])

                # Determine radius based on place type
                place_type = data[0].get("addresstype", data[0].get("type", ""))

                if place_type in ["country"]:
                    radius = 500000  # 500km
                elif place_type in ["state"]:
                    radius = 200000  # 200km
                elif place_type in ["county", "region"]:
                    radius = 60000  # 60km
                elif place_type in ["city", "municipality"]:
                    radius = 30000  # 30km
                elif place_type in ["town", "village", "suburb"]:
                    radius = 5000  # 5km
                else:
                    radius = 10000  # 10km default

                return Location(lat, lon, radius, bounding_box)

            return None
        except Exception as e:
            print(f"Error fetching coordinates for {location_name}: {e}")
            return None

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "radius": self.radius,
            "bounding_box": self.bounding_box,
        }
