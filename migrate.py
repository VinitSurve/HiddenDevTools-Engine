import importlib
import sys

from migrations.discover import discover
from migrations.logger import title

from migrations.history import (
    has_run,
    mark_run,
)

def main():

    migrations = discover()

    if len(sys.argv) == 1:

        title("HiddenDevTools Migration Framework")

        print()

        for migration in migrations:

            module = importlib.import_module(
                f"migrations.scripts.{migration}"
            )

            print(f"{migration.split('_')[0]}  {module.NAME}")

        print()

        return

    migration_number = sys.argv[1]

    target = None

    for migration in migrations:

        if migration.startswith(migration_number):

            target = migration

            break

    if target is None:

        print("Migration not found.")

        return

    module = importlib.import_module(
        f"migrations.scripts.{target}"
    )

    title(module.NAME)

    module.run()

    if has_run(module.NUMBER):

        print()

        print("Migration already executed.")

        return

    mark_run(
    module.NUMBER
)
    


if __name__ == "__main__":

    main()