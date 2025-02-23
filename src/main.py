from CubeSat import CubeSat
from GroundStation import GroundStation


def main():
    ground_station = GroundStation("GS")

    # Create a hashchain of length 100 starting from a random seed
    seed = ground_station.generate_random_token(32)
    # 'f6019e6460f1e40d8f463deb1661989b2653f6eb19a0a0f64111038f017d804f'
    # ground_station.generate_random_token(32)
    hashchain = ground_station.create_hashchain(seed, 10000)

    # Use the last token from the hashchain as the initial token for CubeSat
    initial_token = hashchain[-1]

    # Create a CubeSat with the initial token
    cubesat = CubeSat(initial_token)

    # Number of software updates to simulate
    num_updates = 3000

    # Send multiple software updates to the CubeSat
    for i in range(1, num_updates + 1):
        # Set the ground station's tokens for this iteration
        ground_station.current_token = hashchain[-(i + 1)]
        ground_station.previous_token = hashchain[-i]

        # Print a separator for clarity
        print(f"--- Sending Software Update {i} ---")

        # Generate a new software update message for each iteration
        software_update = f"CubeSat software update {i}"

        transmission_token = ground_station.send_update(software_update)
        # print("transmission_token", transmission_token)

        # Receive the software update from the ground station
        if i == 1:
            cubesat.receive_update(software_update, transmission_token, True)
        else:
            cubesat.receive_update(software_update, transmission_token, False)
        print()

    print("All software updates processed.")


main()
