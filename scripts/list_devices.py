import sounddevice as sd


def main() -> None:
    print("Input devices:")
    for d in sd.query_devices():
        print(d)


if __name__ == "__main__":
    main()

