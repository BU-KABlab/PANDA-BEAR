class Wells:
    def __init__(self):
        self.wells = {}
        for row in "ABCDEFGH":
            for col in range(1, 13):
                well_id = row + str(col)
                if well_id == "A1":
                    coordinates = {"x": 10, "y": 10, "z": -30}
                    contents = None
                    volume = 0
                else:
                    coordinates = {"x": None, "y": None, "z": None}
                    contents = None
                    volume = 0
                self.wells[well_id] = {"coordinates": coordinates, "contents": contents, "volume": volume}
    def get_coordinates(self, well_id):
        coordinates_dict = self.wells[well_id]["coordinates"]
        coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_list

class Vial:
    def __init__(self, x, y, z, contents, volume):
        self.coordinates = {"x": x, "y": y, "z": z}
        self.contents = contents
        self.volume = volume
    def get_volume(self):
        return self.volume