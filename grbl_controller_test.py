import grbl_cnc_mill as grbl

# Set up the mill connection
mill = grbl.MockMill()


with mill as mill:
    # Mill will connect to default connections and home the machine
    print(f"Connection opened: {mill.ser_mill.is_open}")

    # Run through all of the functions in the Mill class


print(f"Connection closed: {mill.ser_mill.is_open}")
