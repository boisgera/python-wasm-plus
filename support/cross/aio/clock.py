import sys
import time
import asyncio

class tui:
    # use direct access, it is absolute addressing on raw terminal.
    out = sys.__stdout__.write

    # save cursor
    def __enter__(self):
        self.out("\x1b7\x1b[?25l")
        return self

    # restore cursor
    def __exit__(self, *tb):
        self.out("\x1b8\x1b[?25h")

    def __call__(self, *a, **kw):
        self.out("\x1b[{};{}H{}".format(kw.get("z", 12), kw.get("x", 40), " ".join(a)))


def step(x=70, y=0, z=2):
    import time

    def box(t, x, y, z):
        lines = t.split("\n")
        fill = "─" * len(t)
        if z > 1:
            print("┌%s┐" % fill, x=x, z=z - 1)
        for t in lines:
            print("│%s│" % t, x=x, z=z)
            z += 1
        print("└%s┘" % fill, x=x, z=z)

    with tui() as print:
        # draw a clock
        t = "%2d:%2d:%2d ☢ 99%% " % time.localtime()[3:6]
        box(t, x=x, y=y, z=z)


async def loop(x=70, y=0, z=2):
    while True:
        step(x, y, z)
        await asyncio.sleep(1)
        sys.stdout.flush()


def start(x=70, y=0, z=2):
    asyncio.create_task(loop(x, y, z))
