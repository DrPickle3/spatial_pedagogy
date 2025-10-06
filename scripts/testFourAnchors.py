import utils


def main():

    sock = utils.connect_wifi()
    utils.screen_init()
    utils.clear_file()

    while True:
        utils.main_loop(sock)


if __name__ == '__main__':
    main()
