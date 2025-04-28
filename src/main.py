from CubeSat import CubeSat
from GroundStation import GroundStation


def main():
    ground_station = GroundStation("GS")

    # Create separate hashchains for each CubeSat
    num_cubesats = 4
    hashchains = [
        ground_station.create_hashchain(ground_station.generate_random_token(32), 10000)
        for _ in range(num_cubesats)
    ]

    # Generate a shared secret for CubeSat communication
    shared_secret = ground_station.generate_random_token(32)

    # Initialize CubeSats with their unique last token from their hashchain
    initial_tokens = [chain[-1] for chain in hashchains]
    # cubesats = [CubeSat(token, shared_secret) for token in initial_tokens]
    cubesats = []
    for idx, token in enumerate(initial_tokens):
        cubesats.append(CubeSat(token, shared_secret, id=idx + 1))

    software_update = "Critical firmware patch v1.3"

    print("\n🔹 [GroundStation] Preparing software update...")
    print(f"   Update content: '{software_update}'")

    # Ground station sends an update to CubeSat1 using its unique hashchain
    print("\n🚀 [GroundStation -> CubeSat1] Sending secure update...")
    ground_station.current_token = hashchains[0][-2]
    ground_station.previous_token = hashchains[0][-1]

    transmission_token = ground_station.send_update(software_update)
    cubesats[0].receive_update(software_update, transmission_token, True)

    print("\n✅ [CubeSat1] Update received & verified!")

    # CubeSat1 broadcasts the update to other CubeSats
    print("\n📡 [CubeSat1] Broadcasting update to other CubeSats...")
    # broadcasted_update, broadcasted_token = cubesats[0].broadcast_update(
    #     software_update
    # )

    # Each CubeSat verifies and logs the result
    for i in range(1, num_cubesats):
        broadcasted_update, broadcasted_token, sender_id, receiver_id, ts = cubesats[
            0
        ].broadcast_update(software_update, idrec=cubesats[i].id)
        print(f"\n🔍 [CubeSat{i+1}] Verifying broadcasted update...")
        cubesats[i].receive_broadcast_update(
            broadcasted_update, broadcasted_token, idsen=sender_id, ts=ts
        )

    print("\nAll software updates processed successfully! 🚀")


main()
