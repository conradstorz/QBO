from loguru import logger
import datetime as dt
import os

@logger.catch
def defineLoggers(filename):
    class Rotator:
        # Custom rotation handler that combines filesize limits with time controlled rotation.
        def __init__(self, *, size, at):
            now = dt.datetime.now()
            self._size_limit = size
            self._time_limit = now.replace(
                hour=at.hour, minute=at.minute, second=at.second
            )
            if now >= self._time_limit:
                # The current time is already past the target time so it would rotate already.
                # Add one day to prevent an immediate rotation.
                self._time_limit += dt.timedelta(days=1)

        def should_rotate(self, message, file):
            file.seek(0, 2)
            if file.tell() + len(message) > self._size_limit:
                return True
            if message.record["time"].timestamp() > self._time_limit.timestamp():
                self._time_limit += dt.timedelta(days=1)
                return True
            return False

    # set rotate file if over 500 MB or at midnight every day
    rotator = Rotator(size=5e8, at=dt.time(0, 0, 0))
    # example useage: logger.add("file.log", rotation=rotator.should_rotate)

    # Begin logging definition
    logger.remove()  # removes the default console logger provided by Loguru.
    # I find it to be too noisy with details more appropriate for file logging.

    # INFO and messages of higher priority only shown on the console.
    # it uses the tqdm module .write method to allow tqdm to display correctly.
    # logger.add(lambda msg: tqdm.write(msg, end=""), format="{message}", level="ERROR")

    logger.configure(handlers=[{"sink": os.sys.stderr, "level": "INFO"}])
    # this method automatically suppresses the default handler to modify the message level

    logger.add(
        "".join(["./LOGS/", filename, "_{time}.log"]),
        rotation=rotator.should_rotate,
        level="DEBUG",
        encoding="utf8",
    )
    # create a new log file for each run of the program
    return
