class PublishingQueue:
    def __init__(self):
        self.queue = []

    def enqueue(self, post_payload: dict):
        """
        Adds a fully generated post payload to the queue.
        """
        self.queue.append(post_payload)

    def get_pending(self) -> list:
        """
        Returns all pending items.
        """
        return self.queue

    def mark_published(self, post_id: str):
        """
        Removes or marks an item as published.
        """
        pass
