import argparse
import utils

def build_arg_parser():
    """Build argument parser."""
    p = argparse.ArgumentParser(
        description="Writing position of Tag with Anchors in CSV"
    )    
    p.add_argument('--display', action='store_true',
                    help='Display real time graphic of position and Anchors')
    return p


def main():

    parser = build_arg_parser()
    args = parser.parse_args()

    sock = utils.connect_wifi()
    args.display and utils.screen_init()
    utils.clear_file()

    try:
        while True:
            utils.main_loop(sock, "../images/test.png", args.display)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()