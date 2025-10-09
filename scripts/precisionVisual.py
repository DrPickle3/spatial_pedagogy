import utils


def main():

    sock = utils.connect_wifi()
    utils.screen_init()
    utils.clear_file()

    try:
        while True:
            utils.main_loop(sock, "../images/test.png")
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()