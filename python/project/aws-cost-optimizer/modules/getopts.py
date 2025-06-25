import sys
import getopt
from typing import List, Tuple

class GetOpts:
    @staticmethod
    def get_opts() -> Tuple[bool, str, str, str, str, str]:
        """Parse command line arguments."""
        help, pods, ns, output, sort, filter = False, '', '', 'text', '', ''
        
        try:
            opts, _ = getopt.getopt(
                sys.argv[1:],
                "hp:n:o:s:f:",
                ["help", "pods=", "namespace=", "output=", "sort=", "filter="]
            )
        except getopt.GetoptError as err:
            print(f"[ERROR] {err}. Please use -h for help.")
            sys.exit(1)

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                help = True
            elif opt in ("-p", "--pods"):
                pods = arg
            elif opt in ("-n", "--namespace"):
                ns = arg
            elif opt in ("-o", "--output"):
                output = arg
            elif opt in ("-s", "--sort"):
                sort = arg
            elif opt in ("-f", "--filter"):
                filter = arg

        return help, pods, ns, output, sort, filter