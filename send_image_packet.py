import argparse
import socket


HOST = "10.1.110.84"
PORT = 28420
TID = "00000003"
SEQUENCE_NUMBER = "0010850050"
AMOUNT = "0001"

# Exact 307-byte TCP application payload from frame 15 of stress.pcap.
# Template values from the capture are replaced by the constants above before
# the bytes are sent.
CAPTURED_PAYLOAD = bytes.fromhex("""
0131392e333630303030303030332020202020202020202020202020323630373037313432303034
464f30303135303030301c42303030311c44301c55301c6530301c68303031303835303035301c71
3b343033333035303037323633333537393d33303033323031313030303032323631303030303f1c
361e453037311e493937381e4f303138303030383236303730373636453545373541373930324139
46343030303030313634363141313636394430303030303030303030303039373830303030303030
303530303030363032313230334130303030301e50303130313232303230303030303039364130
3030303030303033313031301e71303139463645303432303730303030301e583030303030301e30
302020202032302020201c391e423036331c47393146413443344203
""")


def build_payload() -> bytes:
    if len(TID) != 8 or not TID.isdigit():
        raise ValueError("TID must contain exactly 8 digits")
    if len(SEQUENCE_NUMBER) != 10 or not SEQUENCE_NUMBER.isdigit():
        raise ValueError("SEQUENCE_NUMBER must contain exactly 10 digits")
    if len(AMOUNT) != 4 or not AMOUNT.isdigit():
        raise ValueError("AMOUNT must contain exactly 4 digits")

    payload = bytearray(CAPTURED_PAYLOAD)

    # TID occupies bytes 6..13 in this SPDH message.
    payload[6:14] = TID.encode("ascii")

    # Field h contains the sequence number.
    sequence_start = payload.index(b"\x1ch") + 2
    payload[sequence_start:sequence_start + 10] = SEQUENCE_NUMBER.encode("ascii")

    # Field B contains the transaction amount.
    amount_start = payload.index(b"\x1cB") + 2
    payload[amount_start:amount_start + 4] = AMOUNT.encode("ascii")

    if len(payload) != 307:
        raise RuntimeError(f"Unexpected SPDH payload length: {len(payload)}")
    return bytes(payload)


def send_packet(host: str, port: int, timeout: float) -> None:
    payload = build_payload()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        print(f"Sent {len(payload)} SPDH bytes to {host}:{port}")
        print(f"TID={TID}, sequence={SEQUENCE_NUMBER}, amount={AMOUNT}")

        sock.settimeout(timeout)
        try:
            response = sock.recv(4096)
        except socket.timeout:
            print("No response received before timeout")
        else:
            print(f"Received {len(response)} bytes: {response.hex(' ')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send the captured SPDH packet over TCP")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    send_packet(args.host, args.port, args.timeout)
