import os


def main():
    timeout_time = int(os.environ.get('TIMEOUT_TIME', 5))


if __name__ == '__main__':
    main()
