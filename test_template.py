from schedule import get_today_schedule

from templates import get_template

today = get_today_schedule()

template = get_template(
    today["Template"]
)

print()

print(template)