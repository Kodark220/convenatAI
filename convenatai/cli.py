from __future__ import annotations
import asyncio

from .run import parse_args, main as run_main


def main() -> None:
    args = parse_args()
    asyncio.run(run_main(args))


if __name__ == "__main__":
    main()
