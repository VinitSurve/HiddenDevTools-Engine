from datetime import datetime

from drive import create_folder


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

folder = create_folder(
    f"DeveloperTools_{timestamp}"
)

print(folder)