from sheet_api import (
    generate_generation_id,
    generated_timestamp,
)


class GenerationService:

    def __init__(self):

        self.id = generate_generation_id()

        self.generated_at = generated_timestamp()